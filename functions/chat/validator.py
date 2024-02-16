from loguru import logger


def validate_page_block_list(lst):
    # Check if lst is a list
    if not isinstance(lst, list):
        logger.warning(f"Input {lst} is not a list")
        return False

    for item in lst:
        # Check if item is a list of length 2
        if not isinstance(item, list) or len(item) != 2:
            logger.warning(f"Inner item {item} is not a list of length 2")
            return False

        # Check if both elements in the sub-list are integers
        if not (isinstance(item[0], str) and isinstance(item[1], str)):
            logger.warning(f"Inner item {item} is not a list of strings")
            return False

        # check those are numbers
        if not (item[0].isdigit() and item[1].isdigit()):
            logger.warning(f"Inner item {item} is not a list of numbers")
            return False

    return True
