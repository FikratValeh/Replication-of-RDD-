#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 26 20:37:19 2023

@author: cesaretvalehov
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import statsmodels.api as sm
from linearmodels.panel import PanelOLS
from linearmodels.compat.statsmodels import Summary
os.chdir('/Users/cesaretvalehov/Desktop/CorporateFinance')

"""
We define book assets as item 6, cash as item 1, inventoriesas item 3, working capital 
as item 4 minus item 5, capital expenditures asitem 128, dividends as the sum of items
19 and 21, long-term debt as item9, short-term debt as item 34 plus item 44, the number 
of common shares asitem 25, the share price as item 199, balance sheet deferred taxes as 
item74, equity issuance as item 108, employment as item 29, the book valueof common equity
 as item 60, and share repurchases as item 115. As inRauh (2006), we define nonpension cash 
 flow as the sum of items 14, 18,and 43
"""
"""
######################### Replication Part 0 ##################################
######################### Data Identification #################################
item = ['6', '1', '3', '4-5', '128', '19+21', '9', '44+34', '25', '199', '74',
        '108', '29', '60', '115', '14+18+43']
identifier = ['AT', 'CHE','INVT', 'ACT-LCT', 'CAPX', 'DVP+DVC', 'DLTT', 'DLC+DD1',
              'CSHO','PRCC','TXDB', 'SSTK', 'EMP', 'CEQ', 'PRSTKC', 'DP+IB+XPR']

conversion_df = ['book assets','cash', 'inventories', 'working capital',
                 'capital expenditures', 'dividends', 'long-term debt',
                 'short-term debt', 'the number of common shares', 
                 'the share price', 'balance sheet deferred taxes', 
                 'equity issuance', 'employment', 'the book value of common equity',
                 'share repurchases', 'nonpension cash flow'] 



df_varnames = pd.DataFrame(list(zip(item, identifier, conversion_df)), 
                           columns = ['Item', 'Identifier', 'Explanation'])

df_varnames.to_excel("Compustat variables.xlsx") 
"""

######################### Replication Part I ##################################
######################### Import and Merge ####################################

######################### Import data for 1990 IRS 5500 #######################
df_IRS_0 = pd.read_excel('1990_data_final.xlsx')
df_IRS_0['CUSIP_ISSUER_NUM'] = df_IRS_0['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_0 = []
for i in df_IRS_0:
    colnames_df_0.append(i)
    
#drop companies without CUSIP number

df_IRS_0 = df_IRS_0[df_IRS_0['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_0 = df_IRS_0[df_IRS_0['TYPE_PENSION_BENEFIT_IND'] == 1]


############ Import data for COMPUSTAT files ##################################

df_comps = pd.read_csv('COMPUSTAT 1990-1998.csv')
df_comps['cusip'] = df_comps['cusip'].astype(str)

#create a new dataframe with 1990 values only

df_comps_0 = df_comps[(df_comps['datadate'].str.startswith('1990'))]

# merge 1990 compustat dataframe with IRS 5500 form on CUSIP

df_comps_0['key'] = df_comps_0['cusip'].str[:6]
df_IRS_0['key'] = df_IRS_0['CUSIP_ISSUER_NUM'].str[:6]
merged_df_0 = pd.merge(df_comps_0, df_IRS_0, on='key')
# drop the key column
merged_df_0.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_0.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast = merged_df_0['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib = merged_df_0['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr = merged_df_0['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost = merged_df_0['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC = []
for i in range(len(pen_ast)):
    MFC.append(norm_cost[i] + fg*(pen_ast[i] - pen_lib[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib = [pen_ast[i] / pen_lib[i] for i in range(len(pen_lib))]
ast_to_lib = [i - 0.6 for i in ast_to_lib]
ast_to_lib = [i * 0.4 for i in ast_to_lib]
ast_to_lib = [0.3 - i for i in ast_to_lib]
ast_to_lib = [min(i, 0.3) for i in ast_to_lib]
funding_gap = [pen_ast[i] - pen_lib[i] for i in range(len(pen_lib))]
DRC = [funding_gap[i] * ast_to_lib[i] for i in range(len(ast_to_lib))]

#adding DRC, MFC AND MPC and FS to the dataframe
###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_0['DRC'] = DRC
merged_df_0['MFC'] = MFC
MPC = []
for i in range(len(merged_df_0)):
    MPC.append(max(merged_df_0['DRC'][i], merged_df_0['MFC'][i]))
merged_df_0['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_0['FS'] = funding_gap

unique_cusip_0 = merged_df_0.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_0:
    average_funding = []
    for j in range(len(merged_df_0)):
        if i == merged_df_0.cusip[j]:
            average_funding.append(merged_df_0.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_0.loc[merged_df_0['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_0:
    average_funding_status = []
    for j in range(len(merged_df_0)):
        if i == merged_df_0.cusip[j]:
            average_funding_status.append(merged_df_0['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_0['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_0.loc[merged_df_0['cusip'] == i, 'FS'] = funding_status
    
merged_df_0 = merged_df_0.drop(['DRC', 'MFC'], axis = 1)       
merged_df_0.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF0', len(merged_df_0)) #drop more than one fundings
merged_df_0.drop_duplicates(subset=['FS'], keep='first', inplace=True)

#Replicate the same thing till 1998

###################1991###################1991###################1991##########
###################1991###################1991###################1991##########
###################1991###################1991###################1991##########

######################### Import data for 1991 IRS 5500 #######################
df_IRS_1 = pd.read_excel('1991_data.xlsx')
df_IRS_1['CUSIP_ISSUER_NUM'] = df_IRS_1['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_1 = []
for i in df_IRS_1:
    colnames_df_1.append(i)
    
#drop companies without CUSIP number

df_IRS_1 = df_IRS_1[df_IRS_1['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_1 = df_IRS_1[df_IRS_1['TYPE_PENSION_BENEFIT_IND'] == 1] #we choose only DB plans


############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1991 values only

df_comps_1 = df_comps[(df_comps['datadate'].str.startswith('1991'))]

# merge 1991 compustat dataframe with IRS 5500 form on CUSIP

df_comps_1['key'] = df_comps_1['cusip'].str[:6]
df_IRS_1['key'] = df_IRS_1['CUSIP_ISSUER_NUM'].str[:6]
merged_df_1 = pd.merge(df_comps_1, df_IRS_1, on='key')
# drop the key column
merged_df_1.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_1.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_1 = merged_df_1['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_1 = merged_df_1['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_1 = merged_df_1['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_1 = merged_df_1['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_1 = []
for i in range(len(pen_ast_1)):
    MFC_1.append(norm_cost_1[i] + fg*(pen_ast_1[i] - pen_lib_1[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_1 = [pen_ast_1[i] / pen_lib_1[i] for i in range(len(pen_lib_1))]
ast_to_lib_1 = [i - 0.6 for i in ast_to_lib_1]
ast_to_lib_1 = [i * 0.4 for i in ast_to_lib_1]
ast_to_lib_1 = [0.3 - i for i in ast_to_lib_1]
ast_to_lib_1 = [min(i, 0.3) for i in ast_to_lib_1]
funding_gap_1 = [pen_ast_1[i] - pen_lib_1[i] for i in range(len(pen_lib_1))]
DRC_1 = [funding_gap_1[i] * ast_to_lib_1[i] for i in range(len(ast_to_lib_1))]


#adding DRC, MFC AND MPC to the dataframe
###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_1['DRC'] = DRC_1
merged_df_1['MFC'] = MFC_1
MPC = []
for i in range(len(merged_df_1)):
    MPC.append(max(merged_df_1['DRC'][i], merged_df_1['MFC'][i]))
merged_df_1['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_1['FS'] = funding_gap_1

unique_cusip_1 = merged_df_1.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_1:
    average_funding = []
    for j in range(len(merged_df_1)):
        if i == merged_df_1.cusip[j]:
            average_funding.append(merged_df_1.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_1.loc[merged_df_1['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_1:
    average_funding_status = []
    for j in range(len(merged_df_1)):
        if i == merged_df_1.cusip[j]:
            average_funding_status.append(merged_df_1['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_1['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_1.loc[merged_df_1['cusip'] == i, 'FS'] = funding_status
    
merged_df_1 = merged_df_1.drop(['DRC', 'MFC'], axis = 1)       
merged_df_1.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_1)) #drop more than one fundings
merged_df_1.drop_duplicates(subset=['FS'], keep='first', inplace=True)





###################1992###################1992###################1992##########
###################1992###################1992###################1992##########
###################1992###################1992###################1992##########

######################### Import data for 1992 IRS 5500 #######################

df_IRS_2 = pd.read_excel('1992_data.xlsx')
df_IRS_2['CUSIP_ISSUER_NUM'] = df_IRS_2['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_2 = []
for i in df_IRS_2:
    colnames_df_2.append(i)
    
#drop companies without CUSIP number

df_IRS_2 = df_IRS_2[df_IRS_2['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_2 = df_IRS_2[df_IRS_2['TYPE_PENSION_BENEFIT_IND'] == 1]


############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1992 values only

df_comps_2 = df_comps[(df_comps['datadate'].str.startswith('1992'))]

# merge 1992 compustat dataframe with IRS 5500 form on CUSIP

df_comps_2['key'] = df_comps_2['cusip'].str[:6]
df_IRS_2['key'] = df_IRS_2['CUSIP_ISSUER_NUM'].str[:6]
merged_df_2 = pd.merge(df_comps_2, df_IRS_2, on='key')
# drop the key column
merged_df_2.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_2.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_2 = merged_df_2['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_2 = merged_df_2['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_2 = merged_df_2['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_2 = merged_df_2['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_2 = []
for i in range(len(pen_ast_2)):
    MFC_2.append(norm_cost_2[i] + fg*(pen_ast_2[i] - pen_lib_2[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_2 = [pen_ast_2[i] / pen_lib_2[i] for i in range(len(pen_lib_2))]
ast_to_lib_2 = [i - 0.6 for i in ast_to_lib_2]
ast_to_lib_2 = [i * 0.4 for i in ast_to_lib_2]
ast_to_lib_2 = [0.3 - i for i in ast_to_lib_2]
ast_to_lib_2 = [min(i, 0.3) for i in ast_to_lib_2]
funding_gap_2 = [pen_ast_2[i] - pen_lib_2[i] for i in range(len(pen_lib_2))]
DRC_2 = [funding_gap_2[i] * ast_to_lib_2[i] for i in range(len(ast_to_lib_2))]

#adding DRC, MFC AND MPC to the dataframe
######### averaging MPCs #########


###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_2['DRC'] = DRC_2
merged_df_2['MFC'] = MFC_2
MPC = []
for i in range(len(merged_df_2)):
    MPC.append(max(merged_df_2['DRC'][i], merged_df_2['MFC'][i]))
merged_df_2['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_2['FS'] = funding_gap_2

unique_cusip_2 = merged_df_2.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_2:
    average_funding = []
    for j in range(len(merged_df_2)):
        if i == merged_df_2.cusip[j]:
            average_funding.append(merged_df_2.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_2.loc[merged_df_2['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_2:
    average_funding_status = []
    for j in range(len(merged_df_2)):
        if i == merged_df_2.cusip[j]:
            average_funding_status.append(merged_df_2['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_2['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_2.loc[merged_df_2['cusip'] == i, 'FS'] = funding_status
    
merged_df_2 = merged_df_2.drop(['DRC', 'MFC'], axis = 1)       
merged_df_2.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_2)) #drop more than one fundings
merged_df_2.drop_duplicates(subset=['FS'], keep='first', inplace=True)




###################1993###################1993###################1993##########
###################1993###################1993###################1993##########
###################1993###################1993###################1993##########

######################### Import data for 1993 IRS 5500 #######################

df_IRS_3 = pd.read_excel('1993_data.xlsx')
df_IRS_3['CUSIP_ISSUER_NUM'] = df_IRS_3['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_3 = []
for i in df_IRS_3:
    colnames_df_3.append(i)
    
#drop companies without CUSIP number

df_IRS_3 = df_IRS_3[df_IRS_3['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_3 = df_IRS_3[df_IRS_3['TYPE_PENSION_BENEFIT_IND'] == 1]


############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1993 values only

df_comps_3 = df_comps[(df_comps['datadate'].str.startswith('1993'))]

# merge 1993 compustat dataframe with IRS 5500 form on CUSIP

df_comps_3['key'] = df_comps_3['cusip'].str[:6]
df_IRS_3['key'] = df_IRS_3['CUSIP_ISSUER_NUM'].str[:6]
merged_df_3 = pd.merge(df_comps_3, df_IRS_3, on='key')
# drop the key column
merged_df_3.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_3.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_3 = merged_df_3['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_3 = merged_df_3['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_3 = merged_df_3['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_3 = merged_df_3['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_3 = []
for i in range(len(pen_ast_3)):
    MFC_3.append(norm_cost_3[i] + fg*(pen_ast_3[i] - pen_lib_3[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_3 = [pen_ast_3[i] / pen_lib_3[i] for i in range(len(pen_lib_3))]
ast_to_lib_3 = [i - 0.6 for i in ast_to_lib_3]
ast_to_lib_3 = [i * 0.4 for i in ast_to_lib_3]
ast_to_lib_3 = [0.3 - i for i in ast_to_lib_3]
ast_to_lib_3 = [min(i, 0.3) for i in ast_to_lib_3]
funding_gap_3 = [pen_ast_3[i] - pen_lib_3[i] for i in range(len(pen_lib_3))]
DRC_3 = [funding_gap_3[i] * ast_to_lib_3[i] for i in range(len(ast_to_lib_3))]


###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_3['DRC'] = DRC_3
merged_df_3['MFC'] = MFC_3
MPC = []
for i in range(len(merged_df_3)):
    MPC.append(max(merged_df_3['DRC'][i], merged_df_3['MFC'][i]))
merged_df_3['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_3['FS'] = funding_gap_3

unique_cusip_3 = merged_df_3.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_3:
    average_funding = []
    for j in range(len(merged_df_3)):
        if i == merged_df_3.cusip[j]:
            average_funding.append(merged_df_3.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_3.loc[merged_df_3['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_3:
    average_funding_status = []
    for j in range(len(merged_df_3)):
        if i == merged_df_3.cusip[j]:
            average_funding_status.append(merged_df_3['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_3['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_3.loc[merged_df_3['cusip'] == i, 'FS'] = funding_status
    
merged_df_3 = merged_df_3.drop(['DRC', 'MFC'], axis = 1)       
merged_df_3.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_3)) #drop more than one fundings
merged_df_3.drop_duplicates(subset=['FS'], keep='first', inplace=True)


###################1994###################1994###################1994##########
###################1994###################1994###################1994##########
###################1994###################1994###################1994##########

######################### Import data for 1994 IRS 5500 #######################

df_IRS_4 = pd.read_excel('1994_data.xlsx')
df_IRS_4['CUSIP_ISSUER_NUM'] = df_IRS_4['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_4 = []
for i in df_IRS_4:
    colnames_df_4.append(i)
    
#drop companies without CUSIP number

df_IRS_4 = df_IRS_4[df_IRS_4['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_4 = df_IRS_4[df_IRS_4['TYPE_PENSION_BENEFIT_IND'] == 1]

############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1994 values only

df_comps_4 = df_comps[(df_comps['datadate'].str.startswith('1994'))]

# merge 1994 compustat dataframe with IRS 5500 form on CUSIP

df_comps_4['key'] = df_comps_4['cusip'].str[:6]
df_IRS_4['key'] = df_IRS_4['CUSIP_ISSUER_NUM'].str[:6]
merged_df_4 = pd.merge(df_comps_4, df_IRS_4, on='key')
# drop the key column
merged_df_4.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_4.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_4 = merged_df_4['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_4 = merged_df_4['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_4 = merged_df_4['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_4 = merged_df_4['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_4 = []
for i in range(len(pen_ast_4)):
    MFC_4.append(norm_cost_4[i] + fg*(pen_ast_4[i] - pen_lib_4[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_4 = [pen_ast_4[i] / pen_lib_4[i] for i in range(len(pen_lib_4))]
ast_to_lib_4 = [i - 0.6 for i in ast_to_lib_4]
ast_to_lib_4 = [i * 0.4 for i in ast_to_lib_4]
ast_to_lib_4 = [0.3 - i for i in ast_to_lib_4]
ast_to_lib_4 = [min(i, 0.3) for i in ast_to_lib_4]
funding_gap_4 = [pen_ast_4[i] - pen_lib_4[i] for i in range(len(pen_lib_4))]
DRC_4 = [funding_gap_4[i] * ast_to_lib_4[i] for i in range(len(ast_to_lib_4))]


###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_4['DRC'] = DRC_4
merged_df_4['MFC'] = MFC_4
MPC = []
for i in range(len(merged_df_4)):
    MPC.append(max(merged_df_4['DRC'][i], merged_df_4['MFC'][i]))
merged_df_4['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_4['FS'] = funding_gap_4

unique_cusip_4 = merged_df_4.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_4:
    average_funding = []
    for j in range(len(merged_df_4)):
        if i == merged_df_4.cusip[j]:
            average_funding.append(merged_df_4.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_4.loc[merged_df_4['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_4:
    average_funding_status = []
    for j in range(len(merged_df_4)):
        if i == merged_df_4.cusip[j]:
            average_funding_status.append(merged_df_4['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_4['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_4.loc[merged_df_4['cusip'] == i, 'FS'] = funding_status
    
merged_df_4 = merged_df_4.drop(['DRC', 'MFC'], axis = 1)       
merged_df_4.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_4)) #drop more than one fundings
merged_df_4.drop_duplicates(subset=['FS'], keep='first', inplace=True)
###################1995###################1995###################1995##########
###################1995###################1995###################1995##########
###################1995###################1995###################1995##########

######################### Import data for 1995 IRS 5500 #######################

df_IRS_5 = pd.read_excel('1995_data.xlsx')
df_IRS_5['CUSIP_ISSUER_NUM'] = df_IRS_5['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_5 = []
for i in df_IRS_5:
    colnames_df_5.append(i)
    
#drop companies without CUSIP number

df_IRS_5 = df_IRS_5[df_IRS_5['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_5 = df_IRS_5[df_IRS_5['TYPE_PENSION_BENEFIT_IND'] == 1]

############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1995 values only

df_comps_5 = df_comps[(df_comps['datadate'].str.startswith('1995'))]

# merge 1995 compustat dataframe with IRS 5500 form on CUSIP

df_comps_5['key'] = df_comps_5['cusip'].str[:6]
df_IRS_5['key'] = df_IRS_5['CUSIP_ISSUER_NUM'].str[:6]
merged_df_5 = pd.merge(df_comps_5, df_IRS_5, on='key')
# drop the key column
merged_df_5.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_5.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_5 = merged_df_5['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_5 = merged_df_5['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_5 = merged_df_5['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_5 = merged_df_5['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_5 = []
for i in range(len(pen_ast_5)):
    MFC_5.append(norm_cost_5[i] + fg*(pen_ast_5[i] - pen_lib_5[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_5 = [pen_ast_5[i] / pen_lib_5[i] for i in range(len(pen_lib_5))]
ast_to_lib_5 = [i - 0.35 for i in ast_to_lib_5]
ast_to_lib_5 = [i * 0.4 for i in ast_to_lib_5]
ast_to_lib_5 = [0.25 - i for i in ast_to_lib_5]
ast_to_lib_5 = [min(i, 0.3) for i in ast_to_lib_5]
funding_gap_5 = [pen_ast_5[i] - pen_lib_5[i] for i in range(len(pen_lib_5))]
DRC_5 = [funding_gap_5[i] * ast_to_lib_5[i] for i in range(len(ast_to_lib_5))]


###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_5['DRC'] = DRC_5
merged_df_5['MFC'] = MFC_5
MPC = []
for i in range(len(merged_df_5)):
    MPC.append(max(merged_df_5['DRC'][i], merged_df_5['MFC'][i]))
merged_df_5['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_5['FS'] = funding_gap_5

unique_cusip_5 = merged_df_5.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_5:
    average_funding = []
    for j in range(len(merged_df_5)):
        if i == merged_df_5.cusip[j]:
            average_funding.append(merged_df_5.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_5.loc[merged_df_5['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_5:
    average_funding_status = []
    for j in range(len(merged_df_5)):
        if i == merged_df_5.cusip[j]:
            average_funding_status.append(merged_df_5['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_5['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_5.loc[merged_df_5['cusip'] == i, 'FS'] = funding_status
    
merged_df_5 = merged_df_5.drop(['DRC', 'MFC'], axis = 1)       
merged_df_5.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_5)) #drop more than one fundings
merged_df_5.drop_duplicates(subset=['FS'], keep='first', inplace=True)

###################1996###################1996###################1996##########
###################1996###################1996###################1996##########
###################1996###################1996###################1996##########

######################### Import data for 1996 IRS 5500 #######################

df_IRS_6 = pd.read_excel('1996_data.xlsx')
df_IRS_6['CUSIP_ISSUER_NUM'] = df_IRS_6['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_6 = []
for i in df_IRS_6:
    colnames_df_6.append(i)
    
#drop companies without CUSIP number

df_IRS_6 = df_IRS_6[df_IRS_6['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_6 = df_IRS_6[df_IRS_6['TYPE_PENSION_BENEFIT_IND'] == 1]

############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1996 values only

df_comps_6 = df_comps[(df_comps['datadate'].str.startswith('1996'))]

# merge 1996 compustat dataframe with IRS 5500 form on CUSIP

df_comps_6['key'] = df_comps_6['cusip'].str[:6]
df_IRS_6['key'] = df_IRS_6['CUSIP_ISSUER_NUM'].str[:6]
merged_df_6 = pd.merge(df_comps_6, df_IRS_6, on='key')
# drop the key column
merged_df_6.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_6.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_6 = merged_df_6['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_6 = merged_df_6['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_6 = merged_df_6['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_6 = merged_df_6['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_6 = []
for i in range(len(pen_ast_6)):
    MFC_6.append(norm_cost_6[i] + fg*(pen_ast_6[i] - pen_lib_6[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_6 = [pen_ast_6[i] / pen_lib_6[i] for i in range(len(pen_lib_6))]
ast_to_lib_6 = [i - 0.35 for i in ast_to_lib_6]
ast_to_lib_6 = [i * 0.4 for i in ast_to_lib_6]
ast_to_lib_6 = [0.25 - i for i in ast_to_lib_6]
ast_to_lib_6 = [min(i, 0.3) for i in ast_to_lib_6]
funding_gap_6 = [pen_ast_6[i] - pen_lib_6[i] for i in range(len(pen_lib_6))]
DRC_6 = [funding_gap_6[i] * ast_to_lib_6[i] for i in range(len(ast_to_lib_6))]


###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_6['DRC'] = DRC_6
merged_df_6['MFC'] = MFC_6
MPC = []
for i in range(len(merged_df_6)):
    MPC.append(max(merged_df_6['DRC'][i], merged_df_6['MFC'][i]))
merged_df_6['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_6['FS'] = funding_gap_6

unique_cusip_6 = merged_df_6.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_6:
    average_funding = []
    for j in range(len(merged_df_6)):
        if i == merged_df_6.cusip[j]:
            average_funding.append(merged_df_6.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_6.loc[merged_df_6['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_6:
    average_funding_status = []
    for j in range(len(merged_df_6)):
        if i == merged_df_6.cusip[j]:
            average_funding_status.append(merged_df_6['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_6['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_6.loc[merged_df_6['cusip'] == i, 'FS'] = funding_status
    
merged_df_6 = merged_df_6.drop(['DRC', 'MFC'], axis = 1)       
merged_df_6.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_6)) #drop more than one fundings
merged_df_6.drop_duplicates(subset=['FS'], keep='first', inplace=True)


###################1997###################1997###################1997##########
###################1997###################1997###################1997##########
###################1997###################1997###################1997##########

######################### Import data for 1997 IRS 5500 #######################

df_IRS_7 = pd.read_excel('1997_data.xlsx')
df_IRS_7['CUSIP_ISSUER_NUM'] = df_IRS_7['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_7 = []
for i in df_IRS_7:
    colnames_df_7.append(i)
    
#drop companies without CUSIP number

df_IRS_7 = df_IRS_7[df_IRS_7['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_7 = df_IRS_7[df_IRS_7['TYPE_PENSION_BENEFIT_IND'] == 1]

############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1997 values only

df_comps_7 = df_comps[(df_comps['datadate'].str.startswith('1997'))]

# merge 1997 compustat dataframe with IRS 5500 form on CUSIP

df_comps_7['key'] = df_comps_7['cusip'].str[:6]
df_IRS_7['key'] = df_IRS_7['CUSIP_ISSUER_NUM'].str[:6]
merged_df_7 = pd.merge(df_comps_7, df_IRS_7, on='key')
# drop the key column
merged_df_7.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_7.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_7 = merged_df_7['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_7 = merged_df_7['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_7 = merged_df_7['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_7 = merged_df_7['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_7 = []
for i in range(len(pen_ast_7)):
    MFC_7.append(norm_cost_7[i] + fg*(pen_ast_7[i] - pen_lib_7[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_7 = [pen_ast_7[i] / pen_lib_7[i] for i in range(len(pen_lib_7))]
ast_to_lib_7 = [i - 0.35 for i in ast_to_lib_7]
ast_to_lib_7 = [i * 0.4 for i in ast_to_lib_7]
ast_to_lib_7 = [0.25 - i for i in ast_to_lib_7]
ast_to_lib_7 = [min(i, 0.3) for i in ast_to_lib_7]
funding_gap_7 = [pen_ast_7[i] - pen_lib_7[i] for i in range(len(pen_lib_7))]
DRC_7 = [funding_gap_7[i] * ast_to_lib_7[i] for i in range(len(ast_to_lib_7))]


###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_7['DRC'] = DRC_7
merged_df_7['MFC'] = MFC_7
MPC = []
for i in range(len(merged_df_7)):
    MPC.append(max(merged_df_7['DRC'][i], merged_df_7['MFC'][i]))
merged_df_7['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_7['FS'] = funding_gap_7

unique_cusip_7 = merged_df_7.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_7:
    average_funding = []
    for j in range(len(merged_df_7)):
        if i == merged_df_7.cusip[j]:
            average_funding.append(merged_df_7.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_7.loc[merged_df_7['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_7:
    average_funding_status = []
    for j in range(len(merged_df_7)):
        if i == merged_df_7.cusip[j]:
            average_funding_status.append(merged_df_7['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_7['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_7.loc[merged_df_7['cusip'] == i, 'FS'] = funding_status
    
merged_df_7 = merged_df_7.drop(['DRC', 'MFC'], axis = 1)       
merged_df_7.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_7)) #drop more than one fundings
merged_df_7.drop_duplicates(subset=['FS'], keep='first', inplace=True)
###################1998###################1998###################1998##########
###################1998###################1998###################1998##########
###################1998###################1998###################1998##########

######################### Import data for 1998 IRS 5500 #######################

df_IRS_8 = pd.read_excel('1998_data.xlsx')
df_IRS_8['CUSIP_ISSUER_NUM'] = df_IRS_8['CUSIP_ISSUER_NUM'].astype(str)

#export column names
colnames_df_8 = []
for i in df_IRS_8:
    colnames_df_8.append(i)
    
#drop companies without CUSIP number

df_IRS_8 = df_IRS_8[df_IRS_8['CUSIP_ISSUER_NUM'] != 'nan']

df_IRS_8 = df_IRS_8[df_IRS_8['TYPE_PENSION_BENEFIT_IND'] == 1]

############ Import data for COMPUSTAT files ##################################

#create a new dataframe with 1998 values only

df_comps_8 = df_comps[(df_comps['datadate'].str.startswith('1998'))]

# merge 1998 compustat dataframe with IRS 5500 form on CUSIP

df_comps_8['key'] = df_comps_8['cusip'].str[:6]
df_IRS_8['key'] = df_IRS_8['CUSIP_ISSUER_NUM'].str[:6]
merged_df_8 = pd.merge(df_comps_8, df_IRS_8, on='key')
# drop the key column
merged_df_8.drop(columns='key', inplace=True)

#merged dataframe is ready! Now drop the IRS CUSIP (becasue it's repeated)
merged_df_8.drop(columns='CUSIP_ISSUER_NUM', inplace=True)


######################### Replication Part II #################################
######################### Data Analysis #######################################

#define variables from IRS form

fg = 0.1 #Funding gap weight

pen_ast_8 = merged_df_8['TOT_ASSETS_BOY_AMT'] #pension plan assets -  - total, beginning of year
pen_lib_8 = merged_df_8['TOT_LIABILITIES_BOY_AMT'] #pension plan liabilities - total, beginning of year
tot_contr_8 = merged_df_8['TOT_CONTRIB_AMT'] #total contributions to the pension plan by working employees in that year
norm_cost_8 = merged_df_8['TOT_DISTRIB_BNFT_AMT'] #normal cost - benefits distributed to the existing retirees in the plan in that year
# MFC = norm_cost+fg*(pen_ast-pen_lib) minimum funding contribution
################################################################
MFC_8 = []
for i in range(len(pen_ast_8)):
    MFC_8.append(norm_cost_8[i] + fg*(pen_ast_8[i] - pen_lib_8[i]))

# DRC = np.min(list1, 0.3*(0.3-0.4(pen_ast/pen_lib - 0.6))) deficit reduction contribution 
################################################################
ast_to_lib_8 = [pen_ast_8[i] / pen_lib_8[i] for i in range(len(pen_lib_8))]
ast_to_lib_8 = [i - 0.35 for i in ast_to_lib_8]
ast_to_lib_8 = [i * 0.4 for i in ast_to_lib_8]
ast_to_lib_8 = [0.25 - i for i in ast_to_lib_8]
ast_to_lib_8 = [min(i, 0.3) for i in ast_to_lib_8]
funding_gap_8 = [pen_ast_8[i] - pen_lib_8[i] for i in range(len(pen_lib_8))]
DRC_8 = [funding_gap_8[i] * ast_to_lib_8[i] for i in range(len(ast_to_lib_8))]


###############################################################################
########################### averaging MPCs ####################################
###############################################################################

merged_df_8['DRC'] = DRC_8
merged_df_8['MFC'] = MFC_8
MPC = []
for i in range(len(merged_df_8)):
    MPC.append(max(merged_df_8['DRC'][i], merged_df_8['MFC'][i]))
merged_df_8['MPC'] = MPC   #MPC is mandatory pension contribution
merged_df_8['FS'] = funding_gap_8

unique_cusip_8 = merged_df_8.cusip.unique().tolist() #take the unique CUSIP values

#sum Mandatory contributions
for i in unique_cusip_8:
    average_funding = []
    for j in range(len(merged_df_8)):
        if i == merged_df_8.cusip[j]:
            average_funding.append(merged_df_8.MPC[j])
    sum_funding = np.sum(average_funding)
    merged_df_8.loc[merged_df_8['cusip'] == i, 'MPC'] = sum_funding

#create average funding status variable
for i in unique_cusip_8:
    average_funding_status = []
    for j in range(len(merged_df_8)):
        if i == merged_df_8.cusip[j]:
            average_funding_status.append(merged_df_8['TOT_ASSETS_BOY_AMT'][j] -
                                          merged_df_8['TOT_LIABILITIES_BOY_AMT'][j])
    funding_status = np.mean(average_funding_status)
    merged_df_8.loc[merged_df_8['cusip'] == i, 'FS'] = funding_status
    
merged_df_8 = merged_df_8.drop(['DRC', 'MFC'], axis = 1)       
merged_df_8.drop_duplicates(subset=['cusip'], keep='first', inplace=True)
print('length DF1', len(merged_df_8)) #drop more than one fundings
merged_df_8.drop_duplicates(subset=['FS'], keep='first', inplace=True)





#finding average funding status
#the idea is to find the rows with the same CUSIP number and then average the funding gaps and
#add it to the last row of the dataframe and then drop all the rows with the same CUSIP
#on average, each firm has 3 pension plans
#Our merge of compustat files  with IRS form data keeps the compustat files same 
#but IRS  data varying based on the plan number



merged_df_0.to_excel('1990_merged.xlsx')
merged_df_1.to_excel('1991_merged.xlsx')
merged_df_2.to_excel('1992_merged.xlsx')
merged_df_3.to_excel('1993_merged.xlsx')
merged_df_4.to_excel('1994_merged.xlsx')
merged_df_5.to_excel('1995_merged.xlsx')
merged_df_6.to_excel('1996_merged.xlsx')
merged_df_7.to_excel('1997_merged.xlsx')
merged_df_8.to_excel('1998_merged.xlsx')




###############################################################################
###############################################################################
###############################################################################
######################### CREATION OF FINAL PANEL #############################


#Import cleaned data files
merged_df_1990 = pd.read_excel('1990_merged.xlsx')
merged_df_1991 = pd.read_excel('1991_merged.xlsx')
merged_df_1992 = pd.read_excel('1992_merged.xlsx')
merged_df_1993 = pd.read_excel('1993_merged.xlsx')
merged_df_1994 = pd.read_excel('1994_merged.xlsx')
merged_df_1995 = pd.read_excel('1995_merged.xlsx')
merged_df_1996 = pd.read_excel('1996_merged.xlsx')
merged_df_1997 = pd.read_excel('1997_merged.xlsx')
merged_df_1998 = pd.read_excel('1998_merged.xlsx')

#first version of panel
panel_first_version  = pd.concat([merged_df_1990, merged_df_1991, merged_df_1992,
                                  merged_df_1993, merged_df_1994, merged_df_1995,
                                  merged_df_1996, merged_df_1997, merged_df_1998],
                                  axis=0)

panel_unbalanced_prime = panel_first_version.sort_values('cusip')

print('average number of years per firm: ', len(panel_unbalanced_prime)/panel_unbalanced_prime.cusip.nunique())

#average number of firms so far is 6.36

#sort by the recorded years and drop repeated years corresponding to one row

unique_cusips = panel_unbalanced_prime.cusip.unique().tolist()
panel_unbalanced = panel_unbalanced_prime.drop(panel_unbalanced_prime.index, axis = 0)

for i in unique_cusips:
    panel_selected = panel_unbalanced_prime[panel_unbalanced_prime['cusip'] == i]
    panel_selected = panel_selected.sort_values('fyear')
    panel_selected = panel_selected.drop_duplicates(subset=['datadate'], keep='first') #sort by the recorded years and drop repeated years corresponding to one row
    panel_unbalanced = pd.concat([panel_unbalanced, panel_selected], axis = 0)
    

panel_unbalanced.to_excel('Unbalanced Panel.xlsx')
#panel_unbalanced = panel_unbalanced.dropna()
panel_unbalanced = panel_unbalanced.reset_index(drop=True)

#preperation of regression vars
inv_to_assts = [panel_unbalanced['capx'][i]/panel_unbalanced['at'][i] for i in range(len(panel_unbalanced))]
nonpension_cash = [panel_unbalanced['dp'][i] + panel_unbalanced['ib'][i] + panel_unbalanced.xpr[i]
                   for i in range(len(panel_unbalanced))]
nonpension_cash_to_assts = [nonpension_cash[i]/panel_unbalanced['at'][i] for i in range(len(panel_unbalanced))]
mc_to_assts = [panel_unbalanced['MPC'][i]/panel_unbalanced['at'][i] for i in range(len(panel_unbalanced))]
fs_to_assts = [panel_unbalanced['FS'][i]/panel_unbalanced['at'][i] for i in range(len(panel_unbalanced))]
MTB = [panel_unbalanced['prcc_f'][i] + panel_unbalanced['csho'][i] for i in range(len(panel_unbalanced))]
MTB = [MTB[i]/ panel_unbalanced['ceq'][i] for i in range(len(panel_unbalanced))]


#add variables back to the unbalanced panel
panel_unbalanced['inv_to_assts'] = inv_to_assts
panel_unbalanced['nonpension_cash_to_assts'] = nonpension_cash_to_assts
panel_unbalanced['mc_to_assts'] = mc_to_assts
panel_unbalanced['fs_to_assets'] = fs_to_assts
panel_unbalanced['MTB_ratio'] = MTB

#READY TO PLAY
#REGRESS FIXED EFFECT ESTIMATES
panel_unbalanced['datadate'] = pd.to_datetime(panel_unbalanced['datadate'])
panel_unbalanced = panel_unbalanced.set_index(['cusip', 'datadate'])

model_raugh = PanelOLS.from_formula('inv_to_assts ~ MTB_ratio + nonpension_cash_to_assts + fs_to_assets + mc_to_assts + TimeEffects + EntityEffects', 
                                    data=panel_unbalanced)
# fit the model and print results
results = model_raugh.fit()
results_summary = results.summary
print(results_summary)
descriptive_statistics = panel_unbalanced.describe()
descriptive_statistics.to_excel('descriptive_statistics of unbalanced panel.xlsx')


