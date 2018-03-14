master_poets = {

    "Romantic": {
        "atts": {
            "jump vel": 1,
            "bounce": 1,
            "elastic": 1
        },
        "William Blake": {
            "visions": True,
        },
        "Mary Robinson": {
        },
        "Robert Burns": {
            "size": .4,
        },
        "William Wordsworth": {
        },
        "Lord Byron": {
            "jump vel": 0,
        },
        "Percy Shelley": {
        },
    },
    "Victorian": {
        "atts": {
            "jump vel": 1.5,
            "bounce": 1,
            "elastic": 1
        },

        "Elizabeth Browning": {
        },
        "Robert Browning": {
        },
        "Thomas Hardy": {
            "accel": 4,
        },
        "Gerard Hopkins": {
        },
        "Alfred Housman": {
        },
    },
    "20C": {
        "atts": {
            "jump vel": .1,
            "bounce": 3,
            "elastic": 4
        },
        "William Yeats": {
            "elastic": 5,
        },
        "Rupert Brooke": {
        },
        "Wilfred Owen": {
            "gas": True,
        },
        "Wystan Auden": {
            "jump vel": 3,
        },
        "Dylan Thomas": {
            "do not go gentle": True,
        },
        "Ted Hughes": {
        },
        "Derek Walcott": {
        },
        "Seamus Heaney": {
        },
        "Elaine Feinstein": {
            "jump vel": 0,
            "accel": .1,
        },
        "Rita Dove": {
            "ground factor": 50,
        },
        "Siegfried Sassoon": {
            "mad jack": 5,
        },
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
                if att not in master_poets[group][poet]:
                    att_dict[att] = master_poets[group]["atts"][att]
            return group, att_dict
    raise Exception("Poet: " + poet + " does not exist.")
