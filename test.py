
def to_power(base, exponent):
    return base ** exponent


def remainder(x, y):
    if x % y != 0:
        return False
    else:
        return True


def get_list(list_arg):
    return_list = []

    for digit in list_arg:
        if remainder(digit, 2):
            return_list.append(digit)

    return return_list


def scramble(word):
    scramble_dict = {'a': 1, 'b': 3, 'c': 3, 'd': 2, 'e': 1, 'f': 4, 'g': 2, 'h': 4, 'i': 1, 'j': 8, 'k': 5, 'l': 1,
                     'm': 3, 'n': 1, 'o': 1, 'p': 3, 'q': 10, 'r': 1, 's': 1, 't': 1, 'u': 1, 'v': 4, 'w': 4, 'x': 8,
                     'y': 4, 'z': 10}

    forbidden_dict = {'!', ',', ' ', '?'}

    score = 0
    for letter in word:
        if letter in forbidden_dict:
            return 'Запрещенный символ!'
        elif letter in scramble_dict:
            score += scramble_dict[letter]

    return score


def factorial(number, current_factorial_value=1):
    if number == 1:
        return current_factorial_value
    else:
        current_factorial_value *= number
        return factorial(number - 1, current_factorial_value)


def fib(x):
    if x < 2:
        return 1
    else:
        return fib(x - 1) + fib(x - 2)


class Complex:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def printout(self):
        print('%d + %di' % (self.a, self.b) if self.b > 0
              else '%d - %di' % (self.a, -self.b) if self.b != 0
                                                  else self.a)


Complex(-1, -1).printout()

Complex(1, -1).printout()

Complex(1, 1).printout()

Complex(1, 0).printout()

from math import acos, cos


class Triangle:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

    def get_corners(self):
        corner_gamma = acos((self.b**2 + self.c**2 - self.a**2)/(2 * self.b * self.c)) * 180/3.14
        corner_delta = acos((self.a**2 + self.b**2 - self.c**2)/(2 * self.a * self.b)) * 180/3.14
        corner_sigma = acos((self.a**2 + self.c**2 - self.b**2)/(2 * self.a * self.c)) * 180/3.14
        return round(corner_gamma), round(corner_delta), round(corner_sigma)

    def get_corners_c_is_none(self, corner_gamma):
        self.c = round(pow(self.a ** 2 + self.b ** 2 - 2 * self.b * self.a * cos(corner_gamma* 3.14/180), 2))
        return self.get_corners()


class Equilateral(Triangle):
    def __init__(self, a):
        self.a = a
        self.b = a
        self.c = a
