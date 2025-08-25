import importlib.util as s

sp = s.spec_from_file_location("main", "backend/src/main.py")
m = s.module_from_spec(sp)
sp.loader.exec_module(m)
print(m.health())
