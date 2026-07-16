class DoublyListNode:
    def __init__(self, x):
        self.val = x
        self.next = None
        self.prev = None
        
def createDoublyLinkedList(arr):
    if not arr:
        return None
    
    head = DoublyListNode(arr[0])
    cur = head

    # for 循环迭代创建双链表
    for val in arr[1:]:
        new_node = DoublyListNode(val)
        cur.next = new_node
        new_node.prev = cur
        cur = cur.next
    
    return head

head = createDoublyLinkedList([1, 2, 3, 4, 5])
tail = None


# 在链表头部插入一个新节点
# new_head = DoublyListNode(0)
# new_head.next = head
# head.prev = new_head
# head = new_head




# 在链表尾部插入一个新节点
# tail = head
# while tail.next is not None:
#     tail = tail.next

# new_node = DoublyListNode(7)
# new_node.prev = tail
# tail.next = new_node
# tail = new_node
# while tail:
#     print(tail.val)
#     tail = tail.prev




# 在链表中间插入一个新节点 1  2  3   4  5
# 需要插入                       22                           
# p = head
# for _ in range(2):
#     p = p.next

# # 组装新节点
# new_node = DoublyListNode(2222)
# new_node.next = p.next
# new_node.prev = p

# # 意思就是哪个的next是新节点，哪个的prev是新节点。。。。记住这个规则就行
# # p.next.prev = new_node
# # p.next = new_node

# # 上面方案和下面方案都ok

# # p.next = new_node
# # new_node.next.prev = new_node

# current = head
# while current:
#     print(current.val)
#     current = current.next



# 删除链表中的某个节点
# head = createDoublyLinkedList([1, 2, 3, 4, 5])

# p = head
# for i in range(2):
#     p = p.next

# p.next.prev = p.prev
# p.prev.next = p.next

# current = head
# while current:
#     print(current.val)
#     current = current.next




# 删除头部节点
# head = createDoublyLinkedList([1, 2, 3, 4, 5])
# head = head.next
# head.prev = None

# current = head
# while current:
#     print(current.val)
#     current = current.next





# 删除尾部节点
# head = createDoublyLinkedList([1, 2, 3, 4, 5])
# p = head
# # 找到尾结点
# while p.next is not None:
#     p = p.next

# p.prev.next = None
# current = head
# while current:
#     print(current.val)
#     current = current.next
