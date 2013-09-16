"""parslisp - an OMeta Lisp via parsley
(http://github.com/python-parsley/parsley)
"""

from collections import namedtuple
from cmd import Cmd
import string
import operator
from parsley import makeGrammar


parser_grammar = '''\
float = <digit+>:lhs '.' <digit+>:rhs -> ['num', float(lhs + '.' + rhs)]
int = <digit+>:i -> ['num', int(i)]
string = '"' <(~'"' anything)*>:s '"' -> s
symbol_char = :x ?(not (x in string.whitespace or x in '()')) -> x
symbol = <symbol_char+>:s -> ['symbol', s]
quote = "'" form:f -> ['quote', f]
atom = float | int | string | quote | symbol

form = quote
     | atom
     | '(' (atom | form):first (ws (atom | form))*:rest ')' -> [first] + rest
'''

parser = makeGrammar(parser_grammar, {'string': string})


eval_grammar = '''\
quote = ["quote" :form] -> form
set = [["symbol" "set!"] ["symbol" :name] eval:value] -> setname(name, value)
if_ = [["symbol" "if"] eval:test ((?(test) eval:result anything)
                                         | anything eval:result)] -> result
define = [["symbol" "define"] [["symbol" :name] ["symbol" anything]*:args]
         anything+:body] -> setname(name, Function(args=[a[1] for a in args],
                                                   env=env.copy(), body=body))

special_forms = quote | set | if_ | define

funcall = [["symbol" anything:f] eval*:args] -> (env[f].invoke(args)
                                                 if f in env
                                                 else primitive_funcs[f](*args))

literal = [("num" | "string") :v] -> v
lookup = ["symbol" :s] -> env[s]

simple = literal | lookup


eval = special_forms
     | funcall
     | simple
     | anything
'''


class Function(namedtuple('Function', 'args env body')):

    def invoke(self, args):
        env = self.env.copy()
        env.update(zip(self.args, args))
        return make_evaluator(env)(self.body).eval()


primitive_funcs = {'+': lambda *args: sum(args),
                   '-': lambda *args: reduce(operator.sub, args),
                   '/': lambda *args: reduce(operator.div, args),
                   '*': lambda *args: reduce(operator.mul, args),
                   '=': lambda *args: reduce(lambda a, b: a == b and b, args),
                   'not': operator.not_}


def make_evaluator(env):

    def setname(name, value):
        env[name] = value
        return value

    return  makeGrammar(eval_grammar, {'primitive_funcs': primitive_funcs,
                                       'env': env,
                                       'setname': setname,
                                       'Function': Function})


class REPL(Cmd):
    prompt = 'parslisp> '

    def __init__(self):
        Cmd.__init__(self)
        self.env = {}
        self.evaluator = make_evaluator(self.env)

    def onecmd(self, line):
        if line.startswith('!'):
            return Cmd.onecmd(self, line[1:])

        parsed = parser(line).form()
        try:
            print self.evaluator([parsed]).eval()
        except Exception as e:
            print repr(e)

    def do_quit(self, arg):
        return True

    def do_env(self, arg):
        print self.env


if __name__ == '__main__':
    import sys
    doc = sys.modules[__name__].__doc__
    REPL().cmdloop(doc)
