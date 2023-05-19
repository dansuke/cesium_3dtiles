from queue import Queue
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import random
import concurrent.futures
import json
from geopy.distance import distance


class ObjectMovement:
    def __init__(self, grid, destination):
        self.grid = grid
        self.destination = destination
        self.directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)] 

    def _bfs(self, start):
        m, n = len(self.grid), len(self.grid[0])
        q = Queue()
        q.put((start, [start]))
        visited = set([start])
        
        while not q.empty():
            (x, y), path = q.get()
            if (x, y) == self.destination:
                return path
            for dx, dy in random.sample(self.directions, 4):
                nx, ny = x + dx, y + dy
                if 0 <= nx < m and 0 <= ny < n and (nx, ny) not in visited:
                    q.put(((nx, ny), path + [(nx, ny)]))
                    visited.add((nx, ny))
        return []

    def _move_objects(self):
        m, n = len(self.grid), len(self.grid[0])
        paths = []
        
        with concurrent.futures.ProcessPoolExecutor() as executor:
            for i in range(m):
                for j in range(n):
                    for _ in range(self.grid[i][j]):
                        paths.append(executor.submit(self._bfs, (i, j)))
        
        paths = [f.result() for f in concurrent.futures.as_completed(paths)]
        return paths
    
    def generate_time_series(self):
        paths = self._move_objects()
        max_length = max(len(path) for path in paths)
        m, n = len(self.grid), len(self.grid[0])
        time_series = []
        for t in range(max_length):
            grid_t = [[0] * n for _ in range(m)]
            for path in paths:
                if t < len(path):
                    x, y = path[t]
                    grid_t[x][y] += 1
            time_series.append(grid_t)
        return time_series


# ランダムな配列を生成
def generate_random_array(width, height, min_value, max_value):
    return np.random.randint(min_value, max_value + 1, size=(height, width))


# アニメーション更新関数
def animate(i):
    heatmap.set_array(data[i])
    return heatmap,


if __name__ == '__main__':
    # 初期設定項目
    mesh_width    = 20           # 横方向のメッシュ個数
    mesh_height   = 20           # 縦方向のメッシュ個数
    destination   = (10, 10)     # どの座標に向かって移動するか
    data_savename = 'data.json'  # 結果（3次元配列）の格納先

    grid = generate_random_array(mesh_width, mesh_height, 0, 2)
    mover = ObjectMovement(grid, destination)
    data  = mover.generate_time_series()
    fig, ax = plt.subplots()
    
    # JSON形式で保存
    heatmap = ax.imshow(data[0], cmap='jet', interpolation='nearest', vmin=0, vmax=20)
    ani = animation.FuncAnimation(fig, animate, frames=len(data), interval=500, blit=True)
    with open(data_savename, 'w') as f:
        json.dump(data, f)

    ani.save("animation.gif", writer='imagemagick')
    # 結果をアニメーション表示
    plt.show()