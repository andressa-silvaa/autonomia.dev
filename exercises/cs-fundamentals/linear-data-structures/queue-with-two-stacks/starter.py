class Queue:
    def __init__(self) -> None:
        raise NotImplementedError

    def enqueue(self, item) -> None:
        raise NotImplementedError

    def dequeue(self):
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
