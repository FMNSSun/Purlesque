import sys
import re
import collections
import os
from functools import reduce

class PList:

  def __init__(self, ls):
    self.ls = ls
    
  def get(self, i):
    return self.ls[i]
    
  def set(self, i, v):
    self.ls[i] = v
    
  def __str__(self):
    return str(self.ls)

class Atom:
  T_I = 0
  T_D = 1
  T_S = 2
  T_V = 3
  T_Q = 4
  T_L = 5
  
  def __init__(self, value, type_of):
    self.value = value
    self.type_of = type_of
    
  def __eq__(self, other):
    if self.type_of != other.type_of:
      return False
      
    return self.value == other.value
  
  def get(self):
    return self.value
    
  def is_int(self):
    return self.type_of == Atom.T_I
    
  def is_double(self):
    return self.type_of == Atom.T_D
    
  def is_string(self):
    return self.type_of == Atom.T_S
    
  def is_verb(self):
    return self.type_of == Atom.T_V
    
  def is_qverb(self):
    return self.type_of == Atom.T_Q
    
  def is_list(self):
    return self.type_of == Atom.T_L
    
  def is_true(self):
    if self.type_of != Atom.T_I:
      return False
      
    return self.value != 0
    
  def __str__(self):
    return "(" + str(self.value) + "|" + str(self.type_of) + ")"
    
  def __repr__(self):
    return self.__str__()
    

class Context:

  def __init__(self, functions):
    self.functions = functions
    self.stacks = [collections.deque()]
    self.location = ("n/a",-1,None)
    
  def push_stack(self):
    self.stacks.append([collections.deque()])
    
  def push_stack_cpy(self):
    self.stacks.append(self.stacks[-1].copy())
    
  def pop_stack(self):
    return self.stacks.pop()
    
  def push(self, atom):
    self.stacks[-1].append(atom)
    
  def pop(self):
    if len(self.stacks[-1]) == 0:
      print(self.location)
      raise Exception("Stack is empty.")
    return self.stacks[-1].pop()
    
  def pop_int(self):
    a = self.pop()
    if not a.is_int():
      raise Exception("Expected I")
    return a
    
  def pop_str(self):
    a = self.pop()
    if not a.is_str():
      raise Exception("Expected S")
    return a
    
  def pop_double(self):
    a = self.pop()
    if not a.is_double():
      raise Exception("Expected D")
    
    
  def pop_verb(self):
    a = self.pop()
    if not a.is_verb():
      raise Exception("Expected V")
    return a
    
  def pop_list(self):
    a = self.pop()
    if not a.is_list():
      raise Exception("Expected L")
    return a
    
  def pop_bool(self):
    a = self.pop()
    if not a.is_int():
      return Atom(1, Atom.T_I)
      
    if a.value == 0:
      return Atom(0, Atom.T_I)
      
    return Atom(1, Atom.T_I)
    
class Builtins:

  @staticmethod
  def call_helper(context, value):
    if hasattr(Builtins, "b_" + value):
      function = getattr(Builtins, "b_" + value)
      function(context)
    else:
      run(context, to_run = value)

  @staticmethod
  def b_dump(context):
    a = context.pop()
    print(a)
    
  @staticmethod
  def b_fail(context):
    print(context.stack)
    print(context.location)
    raise Exception("I had to fail")

  @staticmethod
  def b_pop(context):
    context.pop()
    
  @staticmethod
  def b_dup(context):
    a = context.pop()
    context.push(a)
    context.push(a)
    
  @staticmethod
  def b_ifcall(context):
    b = context.pop_verb()
    a = context.pop_bool()
    if(a.value != 0):
      Builtins.call_helper(context, b.value)

  @staticmethod
  def b_ifncall(context):
    b = context.pop_verb()
    a = context.pop_bool()
    if(a.value == 0):
      Builtins.call_helper(context, b.value)
          
  @staticmethod
  def b_equ(context):
    b = context.pop()
    a = context.pop()
    if a == b:
      context.push(Atom(1, Atom.T_I))
    else:
      context.push(Atom(0, Atom.T_I))
      
  @staticmethod
  def b_neq(context):
    b = context.pop()
    a = context.pop()
    if a == b:
      context.push(Atom(0, Atom.T_I))
    else:
      context.push(Atom(1, Atom.T_I))
      
  @staticmethod
  def b_execute(context):
    a = context.pop_verb()
    context.push_stack_cpy()
    Builtins.call_helper(context, a.value)
    s = context.pop_stack()
    
    for e in s:
      context.push(e)
    
  @staticmethod
  def b_add(context):
    a = context.pop()
    b = context.pop()
    
    if a.is_int() and b.is_int():
      context.push(Atom(a.value + b.value, Atom.T_I))
    
def run(context, to_run = "main",):
  function = context.functions[to_run]
  context.location = (to_run,-1)
  
  i = 0

  for atom in function:
    context.location = (to_run, i, atom)
    if atom.is_verb():
      if hasattr(Builtins, "b_" + atom.value):
        getattr(Builtins, "b_" + atom.value)(context)
      else:
        run(context, atom.value)
    elif atom.is_qverb():
      context.push(Atom(atom.value, Atom.T_V))
    else:
      context.push(atom)
    i += 1
    
  
def parse(contents, imports={}):
  global INCLUDE_DIR
  functions = contents.split(";")
  fns = {}
  for function in functions:
    atms = []
    tokens = function.split()
    if(len(tokens) > 0):
      name = tokens[0]
      tokens = tokens[1:]
      for token in tokens:
        if re.match("^@(.*)$", token):
          path = INCLUDE_DIR + token[1:]
          if(path in imports):
            continue
          imports[path] = True
          contents_ = load_contents(path)
          fns.update(parse(contents_, imports))
        elif re.match("^-?[0-9]+$", token):
          atms.append(Atom(int(token,10), Atom.T_I))
        elif re.match("^-?[0-9]+\.[0-9]*$", token):
          atms.append(Atom(float(token), Atom.T_D))
        elif re.match("^\"(.*)\"$", token):
          atms.append(Atom(token[1:-1], Atom.T_S))
        elif re.match("^&[a-zA-Z_]{1}[a-zA-Z_0-9]*$", token):
          atms.append(Atom(token[1:], Atom.T_Q))
        elif re.match("^[a-zA-Z_]{1}[a-zA-Z_0-9]*$", token):
          atms.append(Atom(token, Atom.T_V))
        else:
          raise Exception("Invalid token :D")
      fns[name] = atms
  return fns

def load_contents(path):
  fhndl = open(path,"r")
  lines = []
  for line in fhndl:
    line = line.strip()
    if line.startswith("#"):
      continue
    lines.append(line)
  fhndl.close()
  return reduce(lambda a,b: a + " " + b, lines)
  
def main():
  if(len(sys.argv) != 3):
    print_usage();
    return None
    
  file = sys.argv[1]
  contents = load_contents(file)
  global INCLUDE_DIR
  INCLUDE_DIR = sys.argv[2]
  
  functions = parse(contents)
  run(Context(functions))
  
def print_usage():
  print("Usage: plsq <file> <include dir>")

if __name__ == "__main__":
  main()