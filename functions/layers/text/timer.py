import time

from loguru import logger


# Context manager to measure the time
class Timer:
    def __init__(self, name, iter_num=None):
        self.name = name
        self.iterator = iter_num

    def __enter__(self):
        self.start_time = time.time()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        total_seconds = time.time() - self.start_time
        if self.iterator is not None and isinstance(self.iterator, int):
            logger.info(
                f"{self.name} took average {total_seconds / self.iterator: .2f} seconds to run {self.iterator} loops"
            )
        else:
            logger.info(f"{self.name} took {total_seconds:.2f} seconds")
