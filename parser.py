import sys


class ParseError(Exception):
    pass


def parse_lockname(string):
    lockname = ''
    i = 0
    while i < len(string) and string[i].lower() in 'abcdefghijklmnopqrstuvwxyz_0123456789':
        lockname += string[i]
        i += 1
    return lockname


def parse_line(line, lock_set):
    instructions = []
    i = 0
    while i < len(line):
        c = line[i]
        match c:
            case '+' | '-' :
                if i > 0 and len(instructions) > 0 and instructions[-1][0] in '+-':
                    if instructions[-1][0] == c:
                        instructions[-1] = (c, instructions[-1][1]+1)
                    else:
                        instructions[-1] = (instructions[-1][0] ,instructions[-1][1]-1)
                        if instructions[-1][1] == 0:
                            instructions = instructions[:-1]
                else:
                    instructions.append((c, 1))
            case '>' | '<':
                if i > 0 and len(instructions) > 0 and instructions[-1][0] in '<>':
                    if instructions[-1][0] == c:
                        instructions[-1] = (c, instructions[-1][1]+1)
                    else:
                        instructions[-1] = (instructions[-1][0] ,instructions[-1][1]-1)
                        if instructions[-1][1] == 0:
                            instructions = instructions[:-1]
                else:
                    instructions.append((c, 1))
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
                instructions.append(('[]', parse_line(line[i+1:close_index], lock_set)))
                i = close_index
            case '?' | '!':
                if len(line) <= i+1:
                    raise ParseError(f'{i} Missing lock name following {c}')
                lockname = parse_lockname(line[i+1:])
                if len(lockname) < 1:
                    raise ParseError(
                        f'{i} Missing/invalid lock name following {c}')
                lock_set.add(lockname)
                instructions.append((c, lockname))
                i += len(lockname)
            case _:
                pass
        i += 1
    return instructions


def parse_file(file_path):
    threads = []
    lock_set = set()
    with open(file_path) as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            instructions = []
            try:
                instructions = parse_line(line, lock_set)
            except ParseError as e:
                raise ParseError(f'{file_path}:{i}:{e}')
            threads.append(instructions)
    return threads, lock_set


if __name__ == '__main__':
    result = []
    if len(sys.argv) > 1:
        result = parse_file(sys.argv[1])
    else:
        while True:
            line = sys.stdin.readline().strip()
            if line == '':
                break
            result.append(parse_line(line))
    for i, thread in enumerate(result):
        print(f'Thread {i}: {thread}')
