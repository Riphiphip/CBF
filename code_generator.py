import parser

operation_register = '%rax'
secondary_op_register = '%r8'
tape_ptr_reg = '%r9'
loop_cmp_reg = '%r10'


def loop_id_gen():
    i = 0
    while True :
        yield i
        i = i+1


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
    result = f'movq ({tape_ptr_reg}), {operation_register}\n'
    result += generate_general_inc(amount, operation_register)
    result += f'movq {operation_register}, ({tape_ptr_reg})\n'
    return result


def generate_dec(amount):
    result = f'movq ({tape_ptr_reg}), {operation_register}\n'
    result += generate_general_dec(amount, operation_register)
    result += f'movq {operation_register}, ({tape_ptr_reg})\n'
    return result


def generate_mov_right(amount):
    return generate_general_inc(amount, tape_ptr_reg)


def generate_mov_left(amount):
    return generate_general_dec(amount, tape_ptr_reg)


def loop_top_lbl(id):
    return f'__cbf_loop_{id}_top'

def loop_bottom_lbl(id):
    return f'__cbf_loop_{id}_bottom'

def generate_loop(body, id_generator):
    id = next(id_generator)
    result = f'{loop_top_lbl(id)}:\n'
    result += f'movq ({tape_ptr_reg}), {loop_cmp_reg}\n'
    result += f'cmp {loop_cmp_reg}, $0\n'
    result += f'je {loop_bottom_lbl(id)}\n'
    result += '\t'.join(generate_statement_sequence(body, id_generator).splitlines(True))
    result += f'\tjmp {loop_top_lbl(id)}\n'
    result += f'{loop_bottom_lbl(id)}:\n'
    return result


def generate_statement_sequence(ir,id_generator):
    result = ''
    for statement in ir:
        match statement:
            case ('+', amount):
                result += generate_inc(amount)
            case ('-', amount):
                result += generate_dec(amount)
            case ('<', amount):
                result += generate_mov_left(amount)
            case ('>', amount):
                result += generate_mov_right(amount)
            case ('[]', body):
                result += generate_loop(body, id_generator)
            case _:
                pass
    return result


tape_label = '__cbf_tape_start'
tape_end_label = '__cbf_tape_end'

def generate_tape_area(size):
    result = f'{tape_label}:\n'
    result += f'\t.skip {size}\n'
    result += f'{tape_end_label}:'
    return result

if __name__ == '__main__':
    ir = parser.parse_file('cbf_scripts/single_thread.cbf')
    a = loop_id_gen()
    with open('local_files/output.s', 'w') as output:
        output.write(generate_statement_sequence(ir[0], a))
