# 循环数组 CycleArray 总结（也称环形数组）

用固定长度数组 + 两个指针实现头尾 O(1) 增删。

## 核心变量

```
arr:  [2, 3, 5, _, _]
       ↑start=0      ↑end=3
```

| 变量 | 含义 |
|------|------|
| `start` | 第一个元素下标，**闭区间**（包含） |
| `end` | 最后一个元素的下一个位置，**开区间**（不包含） |
| `count` | 当前元素个数 |
| `size` | 数组容量 |

有效元素在环上**连续存储**，不会出现 `[2, _, 3, _, 5]` 这种中间空洞。

---

## 口诀

**先对准要操作的位置，操作完再更新指针。**

| 指针 | 指向 | 添加 | 删除 |
|------|------|------|------|
| `start` 闭 | 第一个元素 | 先移再写 | 先清再移 |
| `end` 开 | 下一个空位 | 先写再移 | 先移再清 |

- 指针**已在**操作位置 → 先操作再移（删头、尾插）
- 指针**不在**操作位置 → 先移再操作（头插写到 start 前、删尾删 end 前一位）

### 代码

```python
# 头插 — 先移再写
self.start = (self.start - 1 + self.size) % self.size
self.arr[self.start] = val

# 删头 — 先清再移
self.arr[self.start] = None
self.start = (self.start + 1) % self.size

# 尾插 — 先写再移
self.arr[self.end] = val
self.end = (self.end + 1) % self.size

# 删尾 — 先移再清
self.end = (self.end - 1 + self.size) % self.size
self.arr[self.end] = None
```

