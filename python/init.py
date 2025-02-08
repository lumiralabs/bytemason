import os

def init(name):
    print(f"Initializing project {name}")
    os.mkdir(name)
    os.mkdir(f"{name}/frontend")
    os.mkdir(f"{name}/supabase")
    raise NotImplementedError("Not implemented")
