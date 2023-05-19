import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from geopy import Point
from geopy.distance import distance


class MeshGrid:
    def __init__(self, origin_lat, origin_lon, mesh_x, mesh_y, mesh_width, mesh_height):
        self.origin_lat = origin_lat
        self.origin_lon = origin_lon
        self.mesh_x = mesh_x
        self.mesh_y = mesh_y
        self.mesh_width = mesh_width
        self.mesh_height = mesh_height
        self.mesh_points = self._create_mesh_points()

    def _create_mesh_points(self):
        mesh_points = np.zeros((self.mesh_height, self.mesh_width, 2))
        for h in range(self.mesh_height):
            for w in range(self.mesh_width):
                current_mesh_origin = distance(meters=self.mesh_x * w).destination(
                    point=distance(meters=self.mesh_y * h).destination(
                        point=Point(self.origin_lat, self.origin_lon), bearing=0),
                    bearing=90
                )
                mesh_points[h, w] = [current_mesh_origin.latitude, current_mesh_origin.longitude]
        return mesh_points


class TimeCZMLPolygonGenerator:
    def __init__(self, mesh_grid, size, color_map, alpha=100):
        self.mesh_grid = mesh_grid
        self.size = size
        self.color_map = color_map
        self.alpha = alpha

    def _create_polygon_data(self, id, name, lat, lon, start_time, end_time, color):
        return {
            "id": id,
            "name": name,
            "availability": f"{start_time}/{end_time}",
            "polygon": {
                "positions": {
                    "cartographicDegrees": self._get_cartographic_degrees(lat, lon)
                },
                "material": {
                    "solidColor": {
                        "color": {
                            "rgba": color + [self.alpha]
                        }
                    }
                },
                "closeTop": True,
                "closeBottom": True
            }
        }

    def _get_cartographic_degrees(self, lat, lon):
        pt0 = self._move_location(lat, lon, -self.size/2, self.size/2)
        pt1 = self._move_location(lat, lon, self.size/2, self.size/2)
        pt2 = self._move_location(lat, lon, self.size/2, -self.size/2)
        pt3 = self._move_location(lat, lon, -self.size/2, -self.size/2)
        return pt0 + pt1 + pt2 + pt3

    def _move_location(self, lat, lon, x, y):
        east_point = distance(meters=x).destination(point=Point(lat, lon), bearing=90)
        east_lat, east_lon = east_point.latitude, east_point.longitude
        north_point = distance(meters=y).destination(point=Point(east_lat, east_lon), bearing=0)
        north_lat, north_lon = north_point.latitude, north_point.longitude
        return [north_lon, north_lat, 0]

    def generate_czml(self, data_list, start_time, interval_sec, file_path):
        end_time = start_time + timedelta(seconds=interval_sec * len(data_list))
        czml_data = [{
            "id": "document",
            "name": "Polygon",
            "version": "1.0",
            "clock": {
                "interval": f"{start_time.isoformat()}/{end_time.isoformat()}",
                "currentTime": start_time.isoformat(),
                "step" : "SYSTEM_CLOCK_MULTIPLIER"
            }
        }]

        for idx, data in enumerate(data_list):
            for i in range(self.mesh_grid.mesh_points.shape[0]):
                for j in range(self.mesh_grid.mesh_points.shape[1]):
                    start_t = start_time + timedelta(seconds=interval_sec * idx)
                    end_t = start_time + timedelta(seconds=interval_sec * (idx+1))
                    mesh_point = self.mesh_grid.mesh_points[i][j]
                    color = self.color_map(data[i][j])
                    czml_data.append(
                        self._create_polygon_data(
                            id=f"mesh{idx}-{i}-{j}", 
                            name=f"{idx}-{i}-{j}", 
                            lat=mesh_point[0], 
                            lon=mesh_point[1], 
                            start_time=start_t.isoformat(), 
                            end_time=end_t.isoformat(), 
                            color=color
                        )
                    )
        with open(file_path, "w") as file:
            json.dump(czml_data, file, indent=4)


def value_to_colorcode(value, min_val, max_val):
    normalized = (value - min_val) / (max_val - min_val)
    colormap = plt.get_cmap('jet')
    rgb = colormap(normalized)[:3]
    rgb = [int(x * 255) for x in rgb]
    return rgb


if __name__ == "__main__":
    # 初期設定項目
    origin_lat   = 35.088699     # 原点座標（北西）の緯度
    origin_lon   = 139.067851    # 原点座標（北西）の経度 
    mesh_size_x  = 20            # 1メッシュあたりのサイズ（x方向・メートル） 
    mesh_size_y  = 20            # 1メッシュあたりのサイズ（y方向・メートル）
    start_time   = datetime(2020, 7, 21, 0, 0, 30, tzinfo=timezone.utc) # シミュレーション開始時刻
    interval_sec = 1             # シミュレーション表示間隔（秒）
    data_name    = 'data.json'   # 読み込むデータ
    save_name    = 'result.czml' # CZML保存名

    with open(data_name, 'r') as f:
        data_list = json.load(f)

    color_map = lambda v: value_to_colorcode(v, 0 , 20)
    mesh_grid = MeshGrid(
        origin_lat=origin_lat, 
        origin_lon=origin_lon, 
        mesh_x=mesh_size_x, 
        mesh_y=mesh_size_y, 
        mesh_width=len(data_list[0]), 
        mesh_height=len(data_list)
    )
    generator = TimeCZMLPolygonGenerator(
        mesh_grid=mesh_grid, 
        size=mesh_size_x, 
        color_map=color_map
    )
    generator.generate_czml(
        data_list=data_list, 
        start_time=start_time, 
        interval_sec=interval_sec, 
        file_path=save_name
    )