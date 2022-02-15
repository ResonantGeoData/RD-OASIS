import pandas as pd
from sklearn.ensemble import RandomForestRegressor  # noqa
import joblib

loaded_model = joblib.load("finalized_model.sav")

var_list = ['Precip', 'Snow', 'Tmean', 'PDD', 'Elev', 'Longitude', 'Latitude', 'Slope', 'Aspect']

ASO_folderpath = './ASO_OASIS/'
ASO_filename = 'ASO_800M_SWE_USCOBR_20190419'
f = ASO_folderpath + ASO_filename + '.csv'

df = pd.read_csv(f)
features = df[var_list]
labels = df['SWE']
predictions = pd.Series(
    loaded_model.predict(features),
    name='Predicted SWE'
)
# NSE = loaded_model.score(features, labels)
# print(round(NSE, 2))
predictions.to_csv(
    ASO_folderpath + ASO_filename + '_swe_predictions.csv',
    index=False
)
