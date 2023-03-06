# import pandas as pd

def convert_interaction(csv, sequence, stream):
    print("Nice")
    # interaction = pd.read_csv(csv)
    interaction = stream
    teller = 0
    list_to_return = []

    # sql = ""
    for x in interaction.values:
        index1 = x[int(sequence[0])]
        index2 = x[int(sequence[1])]
        if sequence[2] != 'none':
            index3 = x[int(sequence[2])]
        else:
            # TODO Change this to another valid date
            index3 = "2000-01-01 01:01:01.000000"
        teller += 1
        list_to_return.append([index1, index2, index3])
    return list_to_return


# string, int, bool,
def convert_metadata(csv, info, source, primaryidn, dataframe):
    # meta = pd.read_csv(csv)
    meta = dataframe
    # insertstatement = ""
    # listofsql = []
    listtoreturn = []
    for x in meta.values:
        teller2 = 0
        for y in info:
            if teller2 == primaryidn:
                teller2 += 1
                continue
            if teller2 != 0:
                insert_list = []
                if y[0] == "String":
                    insert_list.append(
                        [x[primaryidn], 'string', y[1], None, x[teller2],
                         source])
                if y[0] == "Numerical":
                    insert_list.append(
                        [x[primaryidn], 'int', y[1], x[teller2], None, source])
                if y[0] == "URL":
                    insert_list.append(
                        [x[primaryidn], 'url', y[1], None, x[teller2], source])
                listtoreturn.append(insert_list)
            teller2 += 1
    return listtoreturn
