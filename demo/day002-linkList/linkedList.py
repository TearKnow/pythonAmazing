class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None

def creatLinkedList(arr) -> ListNode:
    if arr is None or len(arr) == 0:
        return None

    head = ListNode(arr[0])
    current = head
    for i in range(1, len(arr)):
        current.next = ListNode(arr[i])
        current = current.next

    return head

head = creatLinkedList([1, 2, 3, 4, 5])

# 删除链表的第一个节点
head = head.next

# 遍历单链表
p = head
while p is not None:
    print(p.val)
    p = p.next

