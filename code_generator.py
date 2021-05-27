
operation_register = '%rax'
secondary_op_register = '%r8'
tape_ptr_reg = '%r9'


class CodeGenError(Exception):
    pass


def generate_general_inc(amount, register):
    if amount <= 0:
        return CodeGenError(
            'Error in IR: Invalid number of increment instructions {amount}'
        )
    result = ''
    while amount > 0:
        if amount == 1:
            result += f'inc {register}\n'
            amount -= 1
        elif amount < 2**32:
            result += f'addq ${hex(amount)}, {register}\n'
            amount -= amount
        else:
            chunk_handled = min(2**64-1, amount)
            result += f'movq ${hex(chunk_handled)}, {secondary_op_register}\n'
            result += f'addq {secondary_op_register}, {register}\n'
            amount -= chunk_handled
    return result


def generate_general_dec(amount, register):
    if amount <= 0:
        return CodeGenError(
            'Error in IR: Invalid number of decrement instructions {amount}'
        )
    result = ''
    while amount > 0:
        if amount == 1:
            result += f'dec {register}\n'
            amount -= 1
        elif amount < 2**32:
            result += f'subq ${hex(amount)}, {register}\n'
            amount -= amount
        else:
            chunk_handled = min(2**64-1, amount)
            result += f'movq ${hex(chunk_handled)}, {secondary_op_register}\n'
            result += f'subq {secondary_op_register}, {register}\n'
            amount -= chunk_handled
    return result


def generate_inc(amount):
    return generate_general_inc(amount, operation_register)


def generate_dec(amount):
    return generate_general_dec(amount, operation_register)


def generate_mov_right(amount):
    return generate_general_inc(amount, tape_ptr_reg)


def generate_mov_left(amount):
    return generate_general_dec(amount, tape_ptr_reg)


if __name__ == '__main__':
    tests = [
        generate_inc(1),
        generate_inc(5),
        generate_inc(2**64),
        generate_dec(1),
        generate_dec(5),
        generate_dec(2**64),
        generate_mov_right(1),
        generate_mov_right(5),
        generate_mov_right(2**64),
        generate_mov_left(1),
        generate_mov_left(5),
        generate_mov_left(2**64),
    ]
    for s in tests:
        print(s)
