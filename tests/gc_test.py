import gc

class_count = {}
for obj in gc.get_objects():
    class_name = type(obj).__name__
    referents = gc.get_referents(obj)
    referents_size = referents.__sizeof__() if hasattr(referents, "__sizeof__") else 0
    class_count.setdefault(class_name, {"count": 0, "memory": 0})
    count = class_count[class_name]["count"] + 1
    memory = class_count[class_name]["memory"] + referents_size
    class_count[class_name] = {"count": count, "memory": memory}

print("Class counts:", class_count)
    