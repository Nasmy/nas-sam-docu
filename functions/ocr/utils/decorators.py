import time

from loguru import logger


# decorator to calculate duration
# taken by any function.
class calculate_time(object):
    def __init__(self, custom_message=None):
        self.custom_message = custom_message

    def __call__(self, func):
        def inner(*args, **kwargs):
            begin = time.perf_counter()
            returned_value = func(*args, **kwargs)
            end = time.perf_counter()

            _verbose = kwargs.get("verbose", True)

            _time_float = float(end - begin)

            if _verbose:
                if _time_float > 1:
                    _time_string = f"{_time_float:.2f} sec"
                elif _time_float > 0.01:
                    _time_string = f"{_time_float * 1000:.0f} ms"
                else:
                    _time_string = f"{_time_float * 1000:.2f} ms"

                if self.custom_message is None:
                    logger.info(f"Total time taken for the function \"{func.__name__}\" is {_time_string}")
                elif "{}" in self.custom_message:
                    logger.info(self.custom_message.format(_time_string))
                else:
                    logger.info(f"{self.custom_message} : {_time_string}")
            return returned_value

        return inner