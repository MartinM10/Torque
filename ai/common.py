import base64
import io

COLOR_LIST = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']


def generate_pc_columns_names(number):
    res = []

    for i in range(number):
        res.append("pc" + str(i))

    return res


def generate_cluster_labels(number):
    res = []

    for i in range(number):
        res.append("Type " + str(i))

    return res


def get_base64(plt, tight=None):
    pic_IObytes = io.BytesIO()
    plt.savefig(pic_IObytes, format='png', bbox_inches=tight)
    pic_IObytes.seek(0)
    return base64.b64encode(pic_IObytes.read())
