"""calc: an arithmetic expression evaluator (tokenizer -> shunting-yard -> RPN evaluation)."""

PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2, "neg": 3, "^": 4}
RIGHT_ASSOC = {"^"}


def tokenize(expr):
    """Split an expression into float numbers, operator strings and parentheses."""
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch.isspace():
            i += 1
        elif ch.isdigit() or ch == ".":
            j = i
            while j < len(expr) and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            tokens.append(float(expr[i:j]))
            i = j
        elif ch in "+-*/%^()":
            tokens.append(ch)
            i += 1
        else:
            raise ValueError("unexpected character: " + ch)
    return tokens


def _binds_tighter(top, tok):
    """Should the operator on the stack be applied before `tok`?"""
    if PRECEDENCE[top] > PRECEDENCE[tok]:
        return True
    return PRECEDENCE[top] == PRECEDENCE[tok] and tok not in RIGHT_ASSOC


def to_rpn(tokens):
    """Shunting-yard: convert infix tokens to reverse Polish notation."""
    output = []
    stack = []
    prev = None
    for tok in tokens:
        if isinstance(tok, float):
            output.append(tok)
        elif tok == "(":
            stack.append(tok)
        elif tok == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("mismatched parentheses")
            stack.pop()
        else:
            unary = tok == "-" and (prev is None or prev == "(" or (isinstance(prev, str) and prev in PRECEDENCE))
            if unary:
                stack.append("neg")
            else:
                while stack and stack[-1] != "(" and _binds_tighter(stack[-1], tok):
                    output.append(stack.pop())
                stack.append(tok)
        prev = tok
    while stack:
        top = stack.pop()
        if top == "(":
            raise ValueError("mismatched parentheses")
        output.append(top)
    return output


def _apply(op, left, right):
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        if right == 0:
            raise ZeroDivisionError("division by zero")
        return left / right
    if op == "%":
        return left % right
    if op == "^":
        return left ** right
    raise ValueError("unknown operator: " + op)


def eval_rpn(rpn):
    """Evaluate a reverse Polish notation token list."""
    stack = []
    for tok in rpn:
        if isinstance(tok, float):
            stack.append(tok)
        elif tok == "neg":
            if not stack:
                raise ValueError("malformed expression")
            stack.append(-stack.pop())
        else:
            if len(stack) < 2:
                raise ValueError("malformed expression")
            right = stack.pop()
            left = stack.pop()
            stack.append(_apply(tok, left, right))
    if len(stack) != 1:
        raise ValueError("malformed expression")
    return stack[0]


def evaluate(expr):
    """Evaluate an expression with + - * / % ^, parentheses and unary minus."""
    return eval_rpn(to_rpn(tokenize(expr)))
