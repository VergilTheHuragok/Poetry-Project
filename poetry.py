master_poets = {

    "Romantic": {
        "atts": {
            "jump vel": 1,
            "bounce": 1,
            "elastic": 1
        },

        "Wordsworth": {
        }
    },
    "Victorian": {
        "atts": {
            "jump vel": 1.1,
            "bounce": 1,
            "elastic": 1
        },

        "Hardy": {
        }
    },
    "20C": {
        "atts": {
            "jump vel": .1,
            "bounce": 3,
            "elastic": 4
        },
        "Auden": {
        }
    }
}


def get_all_poets():
    poet_list = []
    for group in master_poets:
        for poet in master_poets[group]:
            if poet != "atts":
                poet_list.append(poet)
    return poet_list


def find_poet(poet):
    poet = poet.title()
    for group in master_poets:
        if poet in master_poets[group]:
            att_dict = master_poets[group][poet]
            for att in master_poets[group]["atts"]:
                att_dict[att] = master_poets[group]["atts"][att]
            return group, att_dict
    raise Exception("Poet: " + poet + " does not exist.")
