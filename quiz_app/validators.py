OPTIONS_PER_QUESTION = 4


def is_valid_question(options, answer):
    """Return True for four distinct text options that contain the answer."""
    if not isinstance(options, list) or len(options) != OPTIONS_PER_QUESTION:
        return False
    if not all(isinstance(option, str) and option.strip()
               for option in options):
        return False
    return len(set(options)) == OPTIONS_PER_QUESTION and answer in options
