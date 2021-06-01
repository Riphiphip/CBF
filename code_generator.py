import parser

class CodeGenError(Exception):
    pass


def register_generator(list):
    for r in list:
        yield r
    error = CodeGenError('Insufficient number of caller saved registers. This message should only appear for compiler developers.')
    yield error
    raise error

# %rdi is not considered a usable register since it is required for lock and unlock calls
# %rsp is not available to preserve stacj alignment
reg_alloc = register_generator(['%rax', '%rcx', '%rdx', '%rsi', '%r8','%r9', '%r10', '%r11'])

operation_register = next(reg_alloc)
secondary_op_register = next(reg_alloc)

loop_cmp_reg = next(reg_alloc)

tape_ptr_reg = next(reg_alloc)
tape_base_reg = next(reg_alloc)
tape_end_reg = next(reg_alloc)

mutex_size = 40

def auto_inc_generator():
    i = 0
    while True :
        yield i
        i = i+1

def indent(string):
    return '\t' + '\t'.join(string.splitlines(True))


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


def tape_cmp_label(id):
    return f'__cbf_mov_{id}_cmp'


def generate_mov_right(amount, id_generator):
    amount = amount * 8
    # id = next(id_generator)
    result = generate_general_inc(amount, tape_ptr_reg)
    # result += f'cmpq {tape_ptr_reg}, {tape_end_reg}\n'
    # result += f'jnge {tape_cmp_label(id)}\n'
    # result += f'subq {tape_end_reg}, {tape_ptr_reg}\n'
    # result += f'addq {tape_base_reg}, {tape_ptr_reg}\n'
    # result += f'{tape_cmp_label(id)}:\n'
    return result 


def generate_mov_left(amount, id_generator):
    amount = amount * 8
    # id = next(id_generator)
    result = generate_general_dec(amount, tape_ptr_reg)
    # result += f'cmpq {tape_ptr_reg}, {tape_base_reg}\n'
    # result += f'jnl {tape_cmp_label(id)}\n'
    # result += f'subq {tape_base_reg}, {tape_ptr_reg}\n'
    # result += f'addq {tape_end_reg}, {tape_ptr_reg}\n'
    # result += f'{tape_cmp_label(id)}:\n'
    return result 


def lock_label(name):
    return f'__cbf_mutex_{name}'

def generate_lock_statement(name):
    result = f'leaq {lock_label(name)}(%rip), %rdi\n'
    result += 'call pthread_mutex_lock@PLT\n'
    return result

def generate_unlock_statement(name):
    result = f'leaq {lock_label(name)}(%rip), %rdi\n'
    result += 'call pthread_mutex_unlock@PLT\n'
    return result

def loop_top_lbl(id):
    return f'__cbf_loop_{id}_top'

def loop_bottom_lbl(id):
    return f'__cbf_loop_{id}_bottom'

def generate_loop(body, id_generator):
    id = next(id_generator)
    result = f'{loop_top_lbl(id)}:\n'
    result += f'movq ({tape_ptr_reg}), {loop_cmp_reg}\n'
    result += f'cmpq $0, {loop_cmp_reg}\n'
    result += f'je {loop_bottom_lbl(id)}\n'
    result += indent(generate_statement_sequence(body, id_generator))
    result += indent(f'jmp {loop_top_lbl(id)}\n')
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
                result += generate_mov_left(amount, id_generator)
            case ('>', amount):
                result += generate_mov_right(amount, id_generator)
            case ('?', name):
                result += generate_lock_statement(name)
            case ('!', name):
                result += generate_unlock_statement(name)
            case ('[]', body):
                result += generate_loop(body, id_generator)
            case _:
                pass
    return result


tape_base_label = '__cbf_tape_start'
tape_end_label = '__cbf_tape_end'

def generate_tape_area(size):
    result = f'.globl {tape_base_label}\n'
    result += f'.comm {tape_base_label}, {hex(size)}\n'
    return result

def generate_lock_area(lock_set):
    result = ''
    for name in lock_set:
        result += f'.globl {lock_label(name)}\n'
        result += f'.comm {lock_label(name)},{hex(mutex_size)},32\n'
    return result

def generate_global_mem(lock_set, tape_size):
    result = '.text\n'
    result += indent(generate_tape_area(tape_size) + '\n')
    result += indent(generate_lock_area(lock_set) + '\n')
    return result

def thread_label(id):
    return f'__cbf_thread_{id}'


def generate_thread_func(body, thread_id, id_generator):
    result = '.text\n'
    result += f'.globl {thread_label(thread_id)}\n'
    result += f'.type {thread_label(thread_id)}, @function\n'
    result += f'{thread_label(thread_id)}:\n'
    result += f'movq $0, {tape_base_reg}\n'
    result += f'pushq {tape_base_reg}\n'
    result += f'leaq {tape_base_label}(%rip), {tape_base_reg}\n'
    # result += f'leaq {tape_end_label}(%rip), {tape_end_reg}\n'
    result += f'movq {tape_base_reg}, {tape_ptr_reg}\n'
    result += indent(generate_statement_sequence(body, id_generator))
    result += indent('movq $0, %rax\n')
    result += indent('movq $0, %rdi\n')
    result += indent('call pthread_exit@PLT\n')
    return result

def generate_main(thread_ids, locks):
    result = '.globl main\n'
    result += '.type main, @function\n'
    result += 'main:\n'
    for name in locks:
        result += indent(f'leaq {lock_label(name)}(%rip), %rdi\n')
        result += indent(f'movq $0, %rsi\n')
        result += indent(f'call pthread_mutex_init@PLT\n')
    for i,id in enumerate(thread_ids):
        result += indent(f'movq $0, %rax\n')
        result += indent(f'push %rax\n')                
        result += indent(f'movq %rsp, %rdi\n')
        result += indent(f'movq $0, %rsi\n')
        result += indent(f'leaq {thread_label(id)}(%rip), %rdx\n')
        result += indent(f'movq $0, %rcx\n')
        result += indent(f'call pthread_create@PLT\n')
        if i+1 < len(thread_ids):
            result += indent(f'push %rax\n')                #Pushes 8B to stack to preserve alignment.
    for _ in thread_ids:
        result += indent(f'movq (%rsp), %rdi\n')
        result += indent(f'movq $0, %rsi\n')
        result += indent(f'call pthread_join@PLT\n')
        result += indent(f'pop %rsi\n')
        result += indent(f'pop %rsi\n')
    result += indent('movq $0, %rax\n')
    result += indent('call exit\n')
    return result

def generate_program(ir, locks, tape_size):
    id_generator = auto_inc_generator()
    result = generate_global_mem(locks, tape_size)
    result +='.text\n'
    result += generate_main(range(0,len(ir)), locks)
    for id,thread in enumerate(ir):
        result += '\n'+generate_thread_func(thread, id, id_generator)
    return result

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        ir, locks = parser.parse_file(sys.argv[1])
        a = auto_inc_generator()
        with open('local_files/output.s', 'w') as output:
            output.write(generate_program(ir, locks, 2**16))
    else:
        print("Missing positional argument \"source\"")
