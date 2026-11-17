import pytest

from calc import eval_rpn, evaluate, to_rpn, tokenize


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("1+2", [1.0, "+", 2.0]),
        (" 12.5 * ( 3 ) ", [12.5, "*", "(", 3.0, ")"]),
        (".5", [0.5]),
        ("", []),
        ("2^3%4", [2.0, "^", 3.0, "%", 4.0]),
        ("7-1/2", [7.0, "-", 1.0, "/", 2.0]),
    ],
    ids=["simple", "spaces", "leading_dot", "empty", "pow_mod", "minus_div"],
)
def test_tokenize(expr, expected):
    """Tokenizer yields floats for numbers and strings for operators and parentheses"""
    assert tokenize(expr) == expected


def test_tokenize_rejects_unknown_characters():
    """Characters outside the grammar are rejected"""
    with pytest.raises(ValueError):
        tokenize("1 $ 2")
    with pytest.raises(ValueError):
        tokenize("1.2.3")


def test_to_rpn_precedence():
    """Multiplication binds tighter than addition"""
    assert to_rpn([1.0, "+", 2.0, "*", 3.0]) == [1.0, 2.0, 3.0, "*", "+"]


def test_to_rpn_parentheses():
    """Parentheses override precedence"""
    assert to_rpn(tokenize("(1+2)*3")) == [1.0, 2.0, "+", 3.0, "*"]


def test_to_rpn_left_associativity():
    """Subtraction and division associate to the left"""
    assert to_rpn(tokenize("1-2-3")) == [1.0, 2.0, "-", 3.0, "-"]
    assert to_rpn(tokenize("8/4/2")) == [8.0, 4.0, "/", 2.0, "/"]


def test_to_rpn_right_associativity():
    """Exponentiation associates to the right"""
    assert to_rpn(tokenize("2^3^2")) == [2.0, 3.0, 2.0, "^", "^"]


def test_to_rpn_unary_minus():
    """A leading minus becomes a unary negation"""
    assert to_rpn(["-", 1.0]) == [1.0, "neg"]


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("1+2", 3),
        ("2+3*4", 14),
        ("(2+3)*4", 20),
        ("10-4-3", 3),
        ("100/10/5", 2),
        ("2^3^2", 512),
        ("2^3", 8),
        ("-2^2", -4),
        ("2*-3", -6),
        ("-(2+3)", -5),
        ("--3", 3),
        ("7%4", 3),
        ("2*3%4", 2),
        ("1.5+2.5", 4),
        ("((1))", 1),
        ("2+3*4^2/8-1", 7),
        ("(1+2)*(3+4)", 21),
        ("4-2*3+1", -1),
        ("2^-1", 0.5),
        ("10%3^2", 1),
        ("5-(-3)", 8),
        ("2 * (3 + 4) - 5 / (1 + 1)", 11.5),
        ("0", 0),
        ("8/4/2", 1),
    ],
)
def test_evaluate(expr, expected):
    """Expressions evaluate with the usual precedence, associativity and unary minus"""
    assert evaluate(expr) == pytest.approx(expected)


@pytest.mark.parametrize(
    "expr,error",
    [
        ("1/0", ZeroDivisionError),
        ("5%0", ZeroDivisionError),
        ("(1+2", ValueError),
        ("1+2)", ValueError),
        ("1+", ValueError),
        ("", ValueError),
        ("1 2", ValueError),
        ("*3", ValueError),
    ],
    ids=["div_zero", "mod_zero", "open_paren", "close_paren", "dangling_op", "empty", "two_numbers", "leading_op"],
)
def test_evaluate_errors(expr, error):
    """Malformed expressions and division by zero raise the right exceptions"""
    with pytest.raises(error):
        evaluate(expr)


def test_eval_rpn_negation_and_subtraction():
    """RPN evaluation handles unary negation and operand order"""
    assert eval_rpn([3.0, "neg"]) == -3.0
    assert eval_rpn([1.0, 2.0, "-"]) == -1.0


def test_eval_rpn_rejects_malformed_input():
    """An empty program or a bare negation is malformed"""
    with pytest.raises(ValueError):
        eval_rpn([])
    with pytest.raises(ValueError):
        eval_rpn(["neg"])
