def error(message):
    print(f"Error: {message}")


def tokenize(expression):
    tokens = []
    i = 0

    while i < len(expression):
        char = expression[i]

        if char.isdigit():
            number = char

            while i + 1 < len(expression) and expression[i + 1].isdigit():
                i += 1
                number += expression[i]

            tokens.append(int(number))

        elif char in "+-*/()^":
            tokens.append(char)

        elif char == " ":
            pass

        else:
            error(f"Invalid character: {char}")
            return None

        i += 1

    return tokens


# -------------------------
# POWER (^)
# -------------------------
def handle_power(tokens):
    i = 0

    while i < len(tokens):
        if tokens[i] == "^":

            if i == 0 or i == len(tokens) - 1:
                error("Invalid power expression")
                return None

            left = tokens[i - 1]
            right = tokens[i + 1]

            result = left ** right

            tokens = tokens[:i - 1] + [result] + tokens[i + 2:]
            i = 0
            continue

        i += 1

    return tokens


# -------------------------
# MUL / DIV
# -------------------------
def handle_mul_div(tokens):
    i = 0

    while i < len(tokens):
        if tokens[i] == "*":
            result = tokens[i - 1] * tokens[i + 1]
            tokens = tokens[:i - 1] + [result] + tokens[i + 2:]
            i = 0
            continue

        elif tokens[i] == "/":
            if tokens[i + 1] == 0:
                error("Division by zero")
                return None

            result = tokens[i - 1] / tokens[i + 1]
            tokens = tokens[:i - 1] + [result] + tokens[i + 2:]
            i = 0
            continue

        i += 1

    return tokens


# -------------------------
# ADD / SUB
# -------------------------
def handle_add_sub(tokens):
    i = 0

    while i < len(tokens):
        if tokens[i] == "+":
            result = tokens[i - 1] + tokens[i + 1]
            tokens = tokens[:i - 1] + [result] + tokens[i + 2:]
            i = 0
            continue

        elif tokens[i] == "-":
            result = tokens[i - 1] - tokens[i + 1]
            tokens = tokens[:i - 1] + [result] + tokens[i + 2:]
            i = 0
            continue

        i += 1

    return tokens


# -------------------------
# PARENTHESES
# -------------------------
def handle_parentheses(tokens):
    while "(" in tokens:

        start = None

        for i, token in enumerate(tokens):
            if token == "(":
                start = i

            elif token == ")" and start is not None:
                inside = tokens[start + 1:i]
                result = bedmas(inside)

                if result is None:
                    return None

                tokens = tokens[:start] + [result] + tokens[i + 1:]
                break

    return tokens


# -------------------------
# MAIN ENGINE (BEDMAS)
# -------------------------
def bedmas(tokens):

    tokens = handle_parentheses(tokens)
    if tokens is None:
        return None

    tokens = handle_power(tokens)
    if tokens is None:
        return None

    tokens = handle_mul_div(tokens)
    if tokens is None:
        return None

    tokens = handle_add_sub(tokens)
    if tokens is None:
        return None

    return tokens[0]


# -------------------------
# ENTRY POINT
# -------------------------
def mathtool_engine(expression):
    tokens = tokenize(expression)

    if tokens is None:
        return

    result = bedmas(tokens)

    if result is not None:
        print(f"Answer: {result}")


print("Welcome to MathTool!")

while True:
    query = input("Enter a math expression: ")
    mathtool_engine(query)