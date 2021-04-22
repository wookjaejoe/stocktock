def strip_multiline_string(s: str):
    new_line = '\n'
    return new_line.join([line.strip() for line in s.split(new_line) if line.strip()])
