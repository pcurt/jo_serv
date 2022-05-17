# Standard lib imports
import logging


class ExampleClass:
    """Dummy class with an empty constructor, used for demonstration purposes"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Instance of {self.__class__.__name__} created")
        pass

    def add(self, a: int, b: int) -> int:
        """Returns the sum of the two inputs

        Args:
            a (int): First number to sum
            b (int): Second number to sum

        Returns:
            int: Sum of the two inputs
        """
        self.logger.debug(f"add method called, with arguments {a} and {b}")
        return a + b
