import sys

class ParseError(Exception):
    pass


def extract_lockname(string):
    lockname = ''
    i = 0
    while i < len(string) and string[i].lower() in 'abcdefghijklmnopqrstuvwxyz_0123456789':
        lockname += string[i]
        i += 1
    return lockname


def parse_line(line):
    instructions = []
    i = 0
    while i < len(line):
        c = line[i]
        match c:
            case '+' | '-' | '>' | '<':
                instructions.append(c)
            case '[':
                if i+1 >= len(line):
                    raise ParseError(f'{i} Unmatched "["')
                depth = 0
                close_index = -1
                for search_i in range(i, len(line)):
                    match line[search_i]:
                        case '[': 
                            depth += 1
                        case ']':
                            depth -= 1
                            if depth == 0:
                                close_index = search_i
                                break
                        case _:
                            pass
                if close_index < 0:
                    raise ParseError(f'{i} Unmatched "["')
                instructions.append(('[]', parse_line(line[i+1:close_index])))
                i = close_index
            case '?' | '!':
                if len(line) <= i+1:
                    raise ParseError(f'{i} Missing lock name following {c}')
                lockname = extract_lockname(line[i+1:])
                if len(lockname)< 1:
                    raise ParseError(
                        f'{i} Missing/invalid lock name following {c}')
                instructions.append((c, lockname))
                i += len(lockname)
            case _:
                pass
        i += 1
    return instructions


def parse_file(file_path):
    threads = []
    with open(file_path) as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            instructions = []
            try:
                instructions = parse_line(line)
            except ParseError as e:
                raise ParseError(f'{file_path}:{i}:{e}')
            threads.append(parse_line(line))
    return threads


if __name__ == '__main__':
    result = []
    if len(sys.argv)>1:
        result = parse_file(sys.argv[1])
    else:
        while True:
            line = sys.stdin.readline().strip()
            if line == '': break
            result.append(parse_line(line))
    for i,thread in enumerate(result):
        print(f'Thread {i}: {thread}')