from bif_lakshay import *
from features_lakshay import *
from fit_lakshay import *
from globals_lakshay import MAX_DEG
import numpy as np

def getCCcoeff(ccs,present_files,ss=225,p="n",ft_thresh=100):
    cc_coeff = {}
    for v in ccs: 
        files = []            
        for f in present_files:
            curr_cc = f.split("-")[0] 
            if v == curr_cc :
                files.append(f)
        if len(files)>0:        
            cc_mp = get_feature_degree(files,ss=ss,p=p,ft_thresh=ft_thresh)
            coeff = getCC(files, cc_mp,p=p)
            cc_coeff[v] = coeff[v]
        #     getRed(files,p="y")
    return cc_coeff 

def getCoeff(cc_coeff):
    vals = {}
    
    # STEP 1: Find the maximum degree across ALL CCAs and ALL features
    global_max_degree = 0
    all_coefficients = []
    
    print("Analyzing polynomial degrees across all CCAs...")
    
    for cc in cc_coeff:
        coeff = cc_coeff[cc]
        if cc not in vals:
            vals[cc] = {}
        for trace in coeff:
            i = 1
            for feature in trace:
                if i not in vals[cc]:
                    vals[cc][i] = []
                
                # Ensure feature is a list/array
                if not isinstance(feature, (list, np.ndarray)):
                    feature = [feature]
                
                degree = len(feature)
                global_max_degree = max(global_max_degree, degree)
                all_coefficients.append(feature)
                vals[cc][i].append(feature)
                i += 1
    
    print(f"Maximum polynomial degree found: {global_max_degree}")
    
    # STEP 2: Standardize ALL coefficient vectors to the same length
    new_vals = {}
    
    for cc in vals:
        new_vals[cc] = {}
        for i in vals[cc]:
            new_vals[cc][i] = {}
            
            # Initialize coefficient arrays
            c_val = {}
            for x in range(global_max_degree):
                c_val[f"c{x}"] = []
            
            # Pad all features to the same length
            for feature in vals[cc][i]:
                # Ensure feature is a numpy array
                feature_array = np.array(feature)
                
                # Pad with zeros to reach global_max_degree
                padded_feature = np.zeros(global_max_degree)
                padded_feature[:len(feature_array)] = feature_array
                
                # Store each coefficient
                for x in range(global_max_degree):
                    c_val[f"c{x}"].append(padded_feature[x])
            
            # Store in new_vals
            for x in range(global_max_degree):
                new_vals[cc][i][f"c{x}"] = c_val[f"c{x}"]
    
    # STEP 3: Verify consistency
    print("\nFeature vector dimensions per CCA:")
    for cc in new_vals:
        if 1 in new_vals[cc]:
            feature_length = len([key for key in new_vals[cc][1].keys() if key.startswith('c')])
            sample_count = len(new_vals[cc][1]['c0']) if 'c0' in new_vals[cc][1] else 0
            print(f"  {cc}: {sample_count} samples, {feature_length} features each")
    
    return vals, new_vals

def getGaussianParams(vals):
    cc_gaussian_params = {}
    for cc in vals:
        if len(list(vals[cc].keys())) == 0:
            continue
        
        # Taking the first feature only
        data = vals[cc][1]
        
        try:
            # Convert to numpy array and check dimensions
            data_array = np.array(data)
            
            if len(data_array) == 0:
                print(f"Warning: No data for {cc}")
                continue
                
            if len(data_array.shape) == 1:
                # If 1D, reshape to 2D
                data_array = data_array.reshape(-1, 1)
            
            print(f"Training Gaussian model for {cc}: {data_array.shape[0]} samples, {data_array.shape[1]} dimensions")
            
            cc_coeff_mean = np.mean(data_array, axis=0)
            
            # Robust covariance estimation
            if data_array.shape[0] > 1:
                coeff_var = np.cov(data_array, rowvar=False)
                
                # Handle 1D case
                if coeff_var.ndim == 0:
                    coeff_var = np.array([[coeff_var]])
                elif coeff_var.ndim == 1:
                    coeff_var = np.diag(coeff_var)
                
                # Add regularization for numerical stability
                regularization = np.eye(coeff_var.shape[0]) * 1e-6
                cc_coeff_var = coeff_var + regularization
            else:
                # Single sample case - use identity matrix
                n_features = len(cc_coeff_mean)
                cc_coeff_var = np.eye(n_features) * 0.1
            
            cc_gaussian_params[cc] = {
                'mean': cc_coeff_mean,
                'covar': cc_coeff_var
            }
            
        except Exception as e:
            print(f"Error creating Gaussian model for {cc}: {e}")
            continue
    
    return cc_gaussian_params

def train(var, present_files, ss=225):
    cc_coeff = getCCcoeff(var, present_files, ss=ss, ft_thresh=1)
    vals, new_vals = getCoeff(cc_coeff)
    cc_gaussian_params = getGaussianParams(vals)
    return vals, new_vals, cc_gaussian_params