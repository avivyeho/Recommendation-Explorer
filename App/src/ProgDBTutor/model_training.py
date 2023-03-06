from pathlib import Path
import random
import numpy as np
import scipy.sparse

import typer

import algorithms_src.util as util
from algorithms_src.algorithm.algorithm import Algorithm

app = typer.Typer()
PathArgument = typer.Argument(
    ...,
    exists=True,
    file_okay=True,
    dir_okay=False,
    writable=False,
    readable=True,
    resolve_path=True,
    help="A readable file."
)
PathWArgument = typer.Argument(
    ...,
    exists=False,
    file_okay=False,
    dir_okay=False,
    writable=True,
    readable=True,
    resolve_path=True,
    help="A file to write to (that doesn't exist yet)"
)

AMOUNT_TEST_USERS = 5
SEED = 5


def run(alg: Algorithm, X: scipy.sparse.csr_matrix, top_k: int = 5):
    """ Train a model and show the recommendations for random users. """
    random.seed(SEED)
    np.random.seed(SEED)

    alg.fit(X)
    return get_recommendation(alg, X, top_k=top_k)


def run_sg(alg: Algorithm, X: scipy.sparse.csr_matrix, test_users: int = 1000,
           perc_history: float = 0.8, top_k: int = 5):
    """ Train a model and calculate recall@k using strong generalization. """
    from algorithms_src.cross_validation.strong_generalization import \
        strong_generalization
    from algorithms_src.metric.recall import recall_k

    random.seed(SEED)
    np.random.seed(SEED)

    Xtrain, Xval_in, Xval_out = strong_generalization(X, test_users=test_users,
                                                      perc_history=perc_history)
    alg.fit(Xtrain)

    predictions = alg.predict(Xval_in)
    recall_scores = recall_k(predictions, Xval_out, top_k)
    avg_recall = np.average(recall_scores)
    info_to_return = (f"Average Recall@{top_k} over {Xval_in.shape[0]} users:" +
                      np.around(avg_recall, decimals=5))
    return info_to_return


def run_wg(alg: Algorithm, X: scipy.sparse.csr_matrix, test_users: int = 1000,
           perc_history: float = 0.8, top_k: int = 5):
    """ Train a model and calculate recall@k using weak generalization. """
    from algorithms_src.cross_validation.weak_generalization import \
        weak_generalization
    from algorithms_src.metric.recall import recall_k

    random.seed(SEED)
    np.random.seed(SEED)

    Xtrain, Xval_in, Xval_out = weak_generalization(X, test_users=test_users,
                                                    perc_history=perc_history)
    alg.fit(Xtrain)

    predictions = alg.predict(Xval_in)
    recall_scores = recall_k(predictions, Xval_out, top_k)
    avg_recall = np.average(recall_scores)
    info_to_return = (f"Average Recall@{top_k} over {Xval_in.shape[0]} users:" +
                      np.around(avg_recall, decimals=5))
    return info_to_return


def get_recommendations(alg: Algorithm, X: scipy.sparse.csr_matrix, users,
                        top_k: int = 5):
    """ Returns a list of contents = (recommendations and their score) for each
    'user' in 'users'."""
    content_list = list()
    for index,user in enumerate(users):
        content_list.append(get_recommendation(alg, X, index, top_k))
    return content_list


def get_recommendation(alg: Algorithm, X: scipy.sparse.csr_matrix, user,
                       top_k: int = 5):
    test_histories = X[user, :]
    predictions = alg.predict(test_histories)
    recommendations, scores = util.predictions_to_recommendations(predictions,
                                                                  top_k=top_k)
    return_list = list()
    return_list.append(recommendations[0])
    return_list.append(scores[0])
    return return_list


def rand(path: Path = PathArgument, item_col: str = "itemId",
         user_col: str = "userId", top_k: int = 5):
    """ Train and predict the Random model. """
    from algorithms_src.algorithm.random import Random

    alg = Random()
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run(alg, X, top_k=top_k)


def iknn(path: Path = PathArgument, item_col: str = "itemId",
         user_col: str = "userId", top_k: int = 5,
         k: int = 200, normalize: bool = False):
    """ Train and predict with the Item KNN model. """
    from algorithms_src.algorithm.item_knn import ItemKNN

    alg = ItemKNN(k=k, normalize=normalize)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run(alg, X, top_k=top_k)


def iknn_sg(path: Path = PathArgument, item_col: str = "itemId",
            user_col: str = "userId", top_k: int = 5,
            k: int = 200, normalize: bool = False, test_users: int = 1000,
            perc_history: float = 0.8):
    """ Train and predict with the EASE model using strong generalization. """
    from algorithms_src.algorithm.item_knn import ItemKNN

    random.seed(SEED)
    np.random.seed(SEED)

    alg = ItemKNN(k, normalize)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_sg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def iknn_wg(path: Path = PathArgument, item_col: str = "itemId",
            user_col: str = "userId", top_k: int = 5,
            k: int = 200, normalize: bool = False, test_users: int = 1000,
            perc_history: float = 0.8):
    """ Train and predict with the EASE model using weak generalization. """
    from algorithms_src.algorithm.item_knn import ItemKNN

    random.seed(SEED)
    np.random.seed(SEED)

    alg = ItemKNN(k, normalize)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_wg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def pop(path: Path = PathArgument, item_col: str = "itemId",
        user_col: str = "userId", top_k: int = 5):
    """ Train and predict the popularity model. """
    from algorithms_src.algorithm.popularity import Popularity

    alg = Popularity()
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run(alg, X, top_k=top_k)


def pop_sg(path: Path = PathArgument, item_col: str = "itemId",
           user_col: str = "userId", top_k: int = 5, test_users: int = 1000,
           perc_history: float = 0.8):
    """ Train and predict the popularity model using strong generalization. """
    from algorithms_src.algorithm.popularity import Popularity

    random.seed(SEED)
    np.random.seed(SEED)

    alg = Popularity()
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_sg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def pop_wg(path: Path = PathArgument, item_col: str = "itemId",
           user_col: str = "userId", top_k: int = 5, test_users: int = 1000,
           perc_history: float = 0.8):
    """ Train and predict the popularity model using weak generalization. """
    from algorithms_src.algorithm.popularity import Popularity

    random.seed(SEED)
    np.random.seed(SEED)

    alg = Popularity()
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_wg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def ease(path: Path = PathArgument, item_col: str = "itemId",
         user_col: str = "userId", top_k: int = 5,
         l2: float = 200.0):
    """ Train and predict with the EASE model. """
    from algorithms_src.algorithm.ease import EASE

    alg = EASE(l2=l2)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run(alg, X, top_k=top_k)


def ease_sg(path: Path = PathArgument, item_col: str = "itemId",
            user_col: str = "userId", top_k: int = 5,
            l2: float = 200.0, test_users: int = 1000,
            perc_history: float = 0.8):
    """ Train and predict with the EASE model using strong generalization. """
    from algorithms_src.algorithm.ease import EASE

    random.seed(SEED)
    np.random.seed(SEED)

    alg = EASE(l2=l2)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_sg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def ease_wg(path: Path = PathArgument, item_col: str = "itemId",
            user_col: str = "userId", top_k: int = 5,
            l2: float = 200.0, test_users: int = 1000,
            perc_history: float = 0.8):
    """ Train and predict with the EASE model using weak generalization. """
    from algorithms_src.algorithm.ease import EASE

    random.seed(SEED)
    np.random.seed(SEED)

    alg = EASE(l2=l2)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_wg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def wmf(path: Path = PathArgument, item_col: str = "itemId",
        user_col: str = "userId", top_k: int = 5,
        alpha: float = 40.0, factors: int = 20, regularization: float = 0.01,
        iterations: int = 20):
    """ Train and predict with the WMF model. """
    from algorithms_src.algorithm.wmf import WMF

    alg = WMF(alpha=alpha, num_factors=factors, regularization=regularization,
              iterations=iterations)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run(alg, X, top_k=top_k)


def wmf_sg(path: Path = PathArgument, item_col: str = "itemId",
           user_col: str = "userId", top_k: int = 5,
           alpha: float = 40.0, factors: int = 20, regularization: float = 0.01,
           iterations: int = 20, test_users: int = 1000,
           perc_history: float = 0.8):
    """ Train and predict with the WMF model using strong generalization. """
    from algorithms_src.algorithm.wmf import WMF

    alg = WMF(alpha=alpha, num_factors=factors, regularization=regularization,
              iterations=iterations)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_sg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def wmf_wg(path: Path = PathArgument, item_col: str = "itemId",
           user_col: str = "userId", top_k: int = 5,
           alpha: float = 40.0, factors: int = 20, regularization: float = 0.01,
           iterations: int = 20, test_users: int = 1000,
           perc_history: float = 0.8):
    """ Train and predict with the WMF model using weak generalization. """
    from algorithms_src.algorithm.wmf import WMF

    alg = WMF(alpha=alpha, num_factors=factors, regularization=regularization,
              iterations=iterations)
    X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    return run_wg(alg, X, test_users=test_users, perc_history=perc_history,
                  top_k=top_k)


def iknn_save(dataframe, model: Path = PathWArgument, k: int = 200,
              normalize: bool = False):
    """ Train the Item KNN model and save it to file. """
    from algorithms_src.algorithm.item_knn import ItemKNN

    alg = ItemKNN(k=k, normalize=normalize)
    dataframe = dataframe[['iid', 'uid']]
    # X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    X = util.df_to_csr(dataframe)
    alg.fit(X).save(model)


def iknn_load(users, matrix, model: Path = PathArgument, top_k: int = 5,
              k: int = 200, normalize: bool = False):
    """ Load an Item KNN model from file and show predictions. """
    from algorithms_src.algorithm.item_knn import ItemKNN

    alg = ItemKNN(k=k, normalize=normalize).load(model)

    return get_recommendations(alg, matrix, users, top_k=top_k)


def pop_save(dataframe, model: Path = PathWArgument, ):
    from algorithms_src.algorithm.popularity import Popularity

    alg = Popularity()
    dataframe = dataframe[['iid', 'uid']]
    # X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    X = util.df_to_csr(dataframe)
    alg.fit(X).save(model)


def pop_load(users, matrix, model: Path = PathWArgument,
             top_k: int = 5):
    from algorithms_src.algorithm.popularity import Popularity

    alg = Popularity().load(model)


    return get_recommendations(alg, matrix, users, top_k=top_k)


def ease_save(dataframe, model: Path = PathWArgument,
              l2: float = 200.0):
    from algorithms_src.algorithm.ease import EASE

    alg = EASE(l2=l2)
    dataframe = dataframe[['uid', 'iid']]
    # X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    X = util.df_to_csr(dataframe)
    alg.fit(X).save(model)


def ease_load(users, matrix,model: Path = PathWArgument, top_k: int = 5, l2: float = 200.0):
    from algorithms_src.algorithm.ease import EASE

    alg = EASE(l2=l2).load(model)
    return get_recommendations(alg, matrix, users, top_k=top_k)


def wmf_save(dataframe, model: Path = PathWArgument, alpha: float = 40.0,
             factors: int = 20,
             regularization: float = 0.01, iterations: int = 20):
    from algorithms_src.algorithm.wmf import WMF

    alg = WMF(alpha=alpha, num_factors=factors, regularization=regularization,
              iterations=iterations)
    dataframe = dataframe[['iid', 'uid']]
    # X = util.path_to_csr(path, item_col=item_col, user_col=user_col)
    X = util.df_to_csr(dataframe)
    alg.fit(X).save(model)

def wmf_load(users, matrix, model: Path = PathWArgument,
             top_k: int = 5, alpha: float = 40.0, factors: int = 20,
             regularization: float = 0.01, iterations: int = 20):
    from algorithms_src.algorithm.wmf import WMF

    alg = WMF(alpha=alpha, num_factors=factors, regularization=regularization,
              iterations=iterations).load(model)

    return get_recommendations(alg, matrix, users, top_k=top_k)



def rand_load(users, matrix, top_k: int = 5):
    """ Train and predict the Random model. """
    from algorithms_src.algorithm.random import Random

    alg = Random()
    return get_recommendations(alg, matrix, users, top_k=top_k)




if __name__ == "__main__":
    app()
