from bson import ObjectId

def serialize_mongo(obj):
    if isinstance(obj, list):
        return [serialize_mongo(i) for i in obj]

    if isinstance(obj, dict):
        return {
            k: serialize_mongo(v)
            for k, v in obj.items()
        }

    if isinstance(obj, ObjectId):
        return str(obj)

    return obj
