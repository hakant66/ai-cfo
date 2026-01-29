from abc import ABC, abstractmethod


class Connector(ABC):
    @abstractmethod
    def test(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def sync(self) -> dict:
        raise NotImplementedError