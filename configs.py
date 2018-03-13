import os


def get_game_root():
    """Gets the path to the root folder of the game"""

    path = os.getcwd().replace("\\", "/")
    if "floobits" in path or "PycharmProjects" in path:
        # Running from interpreter
        path_parts = path.split("/")
        path = path_parts[0] + "/" + path_parts[1] + "/" + path_parts[
            2] + "/Desktop/Poetry Project"
    else:
        # Running from compiled source
        path = path[:path.rfind("/")]

    return path + "/"