import os
import glob
import re
import xml.etree.ElementTree as xml_item
import json
from collections import defaultdict
import csv
import pprint

###Functions###

def xml_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(xml_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
              d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

#Remove extraneous lead data on dictionary keys
def transform(multilevelDict):
        return {str(key).replace('urn','') :
        (transform(value) if isinstance(value, dict) else value) for key, value
        in multilevelDict.items()}

#Extract last directory string
def last_dir(input_str):
    s = input_str[::-1] #reverse string
    lst = s.split('/')
    s = lst[0]
    s = s[::-1]
    return s

#Check id string has numerals
def hasNumbers(input_str):
    return any(char.isdigit() for char in input_str)

def pretty_diction(obj):
    return json.dumps(obj, sort_keys=True, indent=8)

def mean(value,total_items):
    return round(value/total_items,3)

def lst_mean(lst, decimal = 4):
    value=0
    total=0
    for item in lst:
        value += float(item)
        total += 1
    if total == 0:
        return "No Data"
    else:
        return round(value/total,decimal)

def overall_pass_percentage(lst):
    total = len(lst)
    pass_num = test_pass_num(lst)

    return 100 * round(pass_num/total, 3)

# Total passing tests
def test_pass_num(lst):
    count = 0
    for item in lst:
        try:
            flot = float(item)
        except:
            continue
        if flot >= .9 and flot <= 1:
            count += 1
    return count

#Total failing tests
def test_fail_num(lst):
    count = 0
    for item in lst:
        try:
            flot = float(item)
        except:
            continue
        if flot < .9 and flot > 0:
            count += 1
    return count

def get_first_word(element):
    return element.split()[0]


###Code###

#Interpretting directory tree
#Directories labeled for testing years
root = os.getcwd()
paths = glob.glob('*')
year_dirs = filter(lambda f: os.path.isdir(f),paths)
year_lst = []
for item in list(year_dirs):
    year_lst.append(item)
#Subdirectories labeled for engine family
test_lst = []
path = glob.glob('*/*')
dirs = filter(lambda f: os.path.isdir(f),path)
#Some tests in subdirectories are labeled for company
company_paths = glob.glob('*/*/*')
co_dirs = filter(lambda f: os.path.isdir(f),company_paths)
co_lst = []

#EDIT AS NEEDED: prevent the addition of non-directories
file_list = ['.pdf','.xlsm','.xlsb','.csv','.xml']

#Generate parent directory for each set of test data
for item in list(dirs):
    directory = str(root + "/" + item)
    for i in file_list:
        if i in item:
            pass
    if hasNumbers(last_dir(item)):
        test_lst.append(directory)
    else:
        for item in list(co_dirs):
            for i in file_list:
                if i in item:
                    pass
            if hasNumbers(last_dir(item)):
                test_lst.append(root + "/" + item)

#parse through individual xml files and generate dictionary
xml_data_dict={}
for item in year_lst:
    year = item
    xml_data_dict[year]= {}
    for test_dir in test_lst:
        if year in test_dir:
            family = last_dir(test_dir)
            xml_data_dict[year][family] = {}
            for filename in os.listdir(test_dir):
                try:
                    if '.xml' in filename:
                        path = test_dir + '/' + filename
                        xml_data = xml_item.parse(path)
                        data = xml_data.getroot()
                        diction = xml_to_dict(data)
                        xml_diction = transform(diction)
                        key = xml_diction['HeavyDutyInUseSubmissionInformation']['TestIdentificationDetails']['TestIdentificationCode']
                        xml_data_dict[year][family][key] = xml_diction
                except:
                    print ("Unable to process filename %s due to unparsable XML" % filename)

#print (pretty_diction(xml_data_dict))

# Generate output file
vehicle_lst = [] #Total Vehicle Count
test_order_lst = [] #Total Number of Test Orders
NTE_counts = {} #Number of NTEs in a test
repeated_vin = 0 #Track non-unique vehicles tests
test_set_means = []
test_set_totals = []
nox_dict = {}
co_dict = {}
pm_dict = {}
miles_dict = {}
bad_ratio = []

fcsv = open('Emissions_Data_Analysis.csv','w')
wr = csv.writer(fcsv, quoting=csv.QUOTE_ALL)

fcsv.write('Individual Test Level Data\n')
fcsv.write('Year, Family, Test ID, VIN Number, NTE Total, Nox Pass Ratio, Co Pass Ratio, PM Pass Ratio\n')

NTE_total = 0
overall_nox_ratio = []
overall_co_ratio = []
overall_pm_ratio = []
nox_pass_lst = []
co_pass_lst = []
pm_pass_lst = []
manu_lst = []
for year in xml_data_dict:
    fcsv.write('\n')
    NTE_counts[year] = {}
    nox_dict[year] = {}
    co_dict[year] = {}
    pm_dict[year] = {}
    miles_dict[year] = {}
    for family in xml_data_dict[year]:
        test_order_lst.append(year[-4:] + ' ' + family)
        NTE_counts[year][family]= {}
        nox_dict[year][family] = {}
        co_dict[year][family] = {}
        pm_dict[year][family] = {}
        miles_dict[year][family] = {}
        for item in xml_data_dict[year][family]:
            top_level = xml_data_dict[year][family][item]['HeavyDutyInUseSubmissionInformation']
            vin = top_level['VehicleTestGroupDetails']['VehicleIdentificationDetails']['VehicleIdentificationNumber']

            if not vin:
                vin = top_level['RecordKeepingDetails']['ProgramRecordDetails']['EngineFamilyRecordDetails']['VehicleRecordDetails']['VehicleIdentificationNumber']
            if vin not in vehicle_lst:
                vehicle_lst.append(vin)
            else:
                repeated_vin += 1
#Pass ratios
            try:
                nox = top_level['VehicleTestGroupDetails']['VehicleTestDetails']['TestSummaryDetails']['NotToExceedSummaryDetails']['VehiclePassRatioNOXValue']
                co = top_level['VehicleTestGroupDetails']['VehicleTestDetails']['TestSummaryDetails']['NotToExceedSummaryDetails']['VehiclePassRatioCOValue']
                pm = top_level['VehicleTestGroupDetails']['VehicleTestDetails']['TestSummaryDetails']['NotToExceedSummaryDetails']['VehiclePassRatioPMValue']

                nox_dict[year][family][item] = {'vin': vin, 'ratio': nox}
                co_dict[year][family][item] = {'vin': vin, 'ratio': co}
                pm_dict[year][family][item] = {'vin': vin, 'ratio': pm}
                try:
                    if top_level['TestIdentificationDetails']['EPAManufacturerCode'] not in manu_lst:
                        manu_lst.append(top_level['TestIdentificationDetails']['EPAManufacturerCode'])
                except:
                    pass
            except:
                continue
            #This skips data storage for badly formed XML
            try:
                if float(nox) <= 1 and float(nox) > 0:
                    nox_pass_lst.append(nox)
            except:
                pass
            try:
                if float(co) <= 1 and float(co) > 0:
                    co_pass_lst.append(co)
            except:
                pass
            try:
                if float(pm) <= 1 and float(pm) > 0:
                    pm_pass_lst.append(pm)
            except:
                pass

            #Create lists to hold all ratio values including non-numerical values
            overall_nox_ratio.append(nox_dict[year][family][item]['ratio'])
            overall_co_ratio.append(co_dict[year][family][item]['ratio'])
            overall_pm_ratio.append(pm_dict[year][family][item]['ratio'])

#Handling for NTE events (not PM NTE events)
            NTE_counts[year][family][item] = 0
            digiyear = re.findall('\d{4,}', year)
            try:
                NTE_data = top_level['VehicleTestGroupDetails']['VehicleTestDetails']['TestSummaryDetails']['NotToExceedEventDetails']
                for event in NTE_data:
                    NTE_counts[year][family][item] += 1
                fcsv.write(str(digiyear[0]) + ',' + str(get_first_word(family)) + ',' + str(item) + ',' + vin + ',' + str(NTE_counts[year][family][item]) + ',')
#Exception indicates that the field did not appear, either could not find in xml or no event
            except:
                fcsv.write(str(digiyear[0]) + ',' + str(get_first_word(family)) + ',' + str(item) + ',' + vin + ', 0,')
                if NTE_counts[year][family][item] == 0:
                    NTE_total += 1
            try:
                fcsv.write('%s, %s, %s \n' % (nox_dict[year][family][item]['ratio'], co_dict[year][family][item]['ratio'], pm_dict[year][family][item]['ratio']))
            except:
                fcsv.write('\n')
                print ("Skipped test %s %s due to badly formed XML" % (family,item))
                pass
            try:
                if float(nox_dict[year][family][item]['ratio']) > 1 or float(co_dict[year][family][item]['ratio']) > 1 or float(pm_dict[year][family][item]['ratio']) > 1:
                    print('Found ratio value in excess of 1 in test %s %s.\n' % (family,item))
                    bad_ratio.append(family + ' ' + item)
            except:
                pass
            try:
                dist = int(top_level['VehicleTestGroupDetails']['VehicleTestDetails']['VehicleBackgroundDetails']['VehicleStopOdometerNumber']) - int(top_level['VehicleTestGroupDetails']['VehicleTestDetails']['VehicleBackgroundDetails']['VehicleStartOdometerNumber'])
                miles_dict[year][family][item] = {'miles': dist}
            except:
                print ('Could not calculate mileage for test %s%s because of missing data.\n' % (family,item))
    fcsv.write('\n')

fcsv.write('\n\nTest Order Level NTE Data\n\n')
fcsv.write('Year, Family, Total NTE, Mean NTE\n')

#Calculate total NTE and averages for test orders
total_tests_performed = 0
for year in NTE_counts:
    for family in NTE_counts[year]:
        overall_count = 0
        total = 0
        for test in NTE_counts[year][family]:
            digiyear = re.findall('\d{4,}', year)
            total_tests_performed += 1
            events = 0
            events += (NTE_counts[year][family][test])
            total += 1
            overall_count += (NTE_counts[year][family][test])
        if total == type(""):
            pass
        if total != 0:
            fcsv.write('%s, %s, %s, %s\n' % (digiyear[0], get_first_word(family), overall_count, mean(overall_count,total)))
            test_set_totals.append(overall_count)
            test_set_means.append(mean(overall_count,total))
        #Handling for if there are no tests
        else:
            fcsv.write('%s, %s, %s, %s,,,,,,,, %s\n' % (digiyear[0], get_first_word(family), overall_count, overall_count, "No tests found excluded from NTE averages"))
fcsv.write('\n')

fcsv.write('\n\nTest Order Level Constituent Data\n\n')
fcsv.write('Year, Family, Low NOX, High NOX, Avg NOX, Low CO, High CO, Avg CO, Low PM, High PM, Avg PM\n')
#Calculate ranges within Test order
for year in nox_dict:
    digiyear = re.findall('\d{4,}', year)
    for family in nox_dict[year]:
        print (get_first_word(family) + "\n")
        nox_high_ratio = 0.00
        nox_low_ratio = 1.00
        co_high_ratio = 0.00
        co_low_ratio = 1.00
        pm_high_ratio = 0.00
        pm_low_ratio = 1.00
        nox_ratios_lst = []
        co_ratios_lst = []
        pm_ratios_lst = []
        for item in nox_dict[year][family]:
            try:
                if float(nox_dict[year][family][item]['ratio']) <= 1:
                    nox_ratios_lst.append(nox_dict[year][family][item]['ratio'])
                    try:
                        if float(nox_dict[year][family][item]['ratio']) > nox_high_ratio:
                            nox_high_ratio = float(nox_dict[year][family][item]['ratio'])
                        if float(nox_dict[year][family][item]['ratio']) < nox_low_ratio:
                            nox_low_ratio = float(nox_dict[year][family][item]['ratio'])
                    except:
                        print('Value is not a numeral')
                else:
                    print('Value in excess of 1, not recorded in ratio list.')
            except:
                print ("%s %s did not contain data for NOX." % (family, item))
            try:
                if float(co_dict[year][family][item]['ratio']) <= 1:
                    co_ratios_lst.append(co_dict[year][family][item]['ratio'])
                    try:
                        if float(co_dict[year][family][item]['ratio']) > co_high_ratio:
                            co_high_ratio = float(co_dict[year][family][item]['ratio'])
                        if float(co_dict[year][family][item]['ratio']) < co_low_ratio:
                            co_low_ratio = float(co_dict[year][family][item]['ratio'])
                    except:
                        print('Value is not a numeral')
                else:
                    print('Value in excess of 1, not recorded in ratio list.')
            except:
                print ("%s %s did not contain data for CO." % (family, item))
            try:
                if float(pm_dict[year][family][item]['ratio']) <= 1:
                    pm_ratios_lst.append(pm_dict[year][family][item]['ratio'])
                    try:
                        if float(pm_dict[year][family][item]['ratio']) > pm_high_ratio:
                            pm_high_ratio = float(pm_dict[year][family][item]['ratio'])
                        if float(pm_dict[year][family][item]['ratio']) < pm_low_ratio:
                            pm_low_ratio = float(pm_dict[year][family][item]['ratio'])
                    except:
                        print('Value is not a numeral')
                else:
                    print('Value in excess of 1, not recorded in ratio list.')
            except:
                print ("%s %s did not contain data for PM." % (family, item))

        fcsv.write('%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s\n' % (digiyear[0], get_first_word(family), nox_low_ratio, nox_high_ratio, lst_mean(nox_ratios_lst), co_low_ratio, co_high_ratio, lst_mean(co_ratios_lst), pm_low_ratio, pm_high_ratio, lst_mean(pm_ratios_lst)))

#Calculate the mean NTE events across all test orders
means = 0
for i in test_set_means:
    means += i
mean = mean(means,len(test_set_means))

fcsv.write('\n\n')
fcsv.write('Top Level Data\n\n')
fcsv.write('Constituent averages and pass counts do not consider tests with data missing\n\n')
fcsv.write('Mileage stats only include tests that recorded less than 500 miles\n\n\n')
fcsv.write('Overall NTE Mean, Total Number of Test Orders, Number of Unique Vehicles, Repeated VINs, Total Manufacturers, Total Tests, Total Tests w/o NTE, Percentage Tests w/o NTE\n')
fcsv.write('%s, %s, %s, %s, %s, %s, %s, %s\n\n' % (mean, len(test_order_lst), len(vehicle_lst), repeated_vin, len(manu_lst), total_tests_performed, NTE_total, (100 * (NTE_total/total_tests_performed))))

#Calculate Mileage
test_mileage = []
recorded_mileage_test_count = 0
low = 1000000000
high = 0

for year in miles_dict:
    for family in miles_dict[year]:
        mileage = 0
        total_tests = 0
        for item in miles_dict[year][family]:
            if miles_dict[year][family][item]['miles'] > 500:
                print ("skipped mileage for test %s %s over 500" % (family,item))
                continue
            if miles_dict[year][family][item]['miles'] <= 1:
                print ("skipped mileage for test %s %s set to 0 or 1" % (family,item))
                continue
            recorded_mileage_test_count += 1
            if miles_dict[year][family][item]['miles'] > high:
                high = miles_dict[year][family][item]['miles']
            if miles_dict[year][family][item]['miles'] < low:
                low = miles_dict[year][family][item]['miles']
            mileage += miles_dict[year][family][item]['miles']
        test_mileage.append(mileage)

total_mileage = 0

for item in test_mileage:
    total_mileage += item

fcsv.write('Total Mileage, Average Mileage, Lowest Mileage, Highest Mileage\n')
fcsv.write('%s, %s, %s, %s\n\n' % (total_mileage, str(total_mileage/recorded_mileage_test_count), low, high))

fcsv.write("Total Nox Pass Count, Total Nox Fail Count, Percentage Passing Nox Tests, Total CO Pass Count, Total CO Fail Count, Percentage Passing CO Tests, Total PM Pass Count, Total PM Fail Count, Percentage Passing PM Tests\n")
fcsv.write("%s,%s,%s,%s,%s,%s,%s,%s,%s\n\n" % (test_pass_num(overall_nox_ratio),test_fail_num(overall_nox_ratio),overall_pass_percentage(nox_pass_lst),test_pass_num(overall_co_ratio),test_fail_num(overall_co_ratio),overall_pass_percentage(co_pass_lst),test_pass_num(overall_pm_ratio),test_fail_num(overall_pm_ratio),overall_pass_percentage(pm_pass_lst)))

vin_dict={}
for item in vehicle_lst:
    vin_dict[item] = {'nox':'','co':'','pm':'','all':''}

for fam in nox_dict:
    for order in nox_dict[fam]:
        for test in nox_dict[fam][order]:
            for item in vin_dict:
                if nox_dict[fam][order][test]['vin'] == item:
                    try:
                        if nox_dict[fam][order][test]['ratio'] == "" or nox_dict[fam][order][test]['ratio'] == "0" or nox_dict[fam][order][test]['ratio'] == "-1" and vin_dict[item]['nox'] != "Pass":
                            vin_dict[item]['nox'] = 'No Data'
                        if float(nox_dict[fam][order][test]['ratio']) >= .9 and float(nox_dict[fam][order][test]['ratio']) <= 1:
                            vin_dict[item]['nox'] = 'Pass'
                        if float(nox_dict[fam][order][test]['ratio']) > 0 and float(nox_dict[fam][order][test]['ratio']) < .9 and vin_dict[item]['nox'] != "Pass":
                            vin_dict[item]['nox'] = "Fail"
                    except:
                        vin_dict[item]['nox'] = 'No Data'

for fam in co_dict:
    for order in co_dict[fam]:
        for test in co_dict[fam][order]:
            for item in vin_dict:
                if co_dict[fam][order][test]['vin'] == item:
                    try:
                        if co_dict[fam][order][test]['ratio'] == "" or co_dict[fam][order][test]['ratio'] == "0" or co_dict[fam][order][test]['ratio'] == "-1" and vin_dict[item]['co'] != "Pass":
                            vin_dict[item]['co'] = 'No Data'
                        if float(co_dict[fam][order][test]['ratio']) >= .9 and float(co_dict[fam][order][test]['ratio']) <= 1:
                            vin_dict[item]['co'] = 'Pass'
                        if float(co_dict[fam][order][test]['ratio']) > 0 and float(co_dict[fam][order][test]['ratio']) < .9 and vin_dict[item]['co'] != "Pass":
                            vin_dict[item]['co'] = "Fail"
                    except:
                        vin_dict[item]['co'] = 'No Data'

for fam in pm_dict:
    for order in pm_dict[fam]:
        for test in pm_dict[fam][order]:
            for item in vin_dict:
                if pm_dict[fam][order][test]['vin'] == item:
                    try:
                        if pm_dict[fam][order][test]['ratio'] == "" or pm_dict[fam][order][test]['ratio'] == "0" or pm_dict[fam][order][test]['ratio'] == "-1" and vin_dict[item]['pm'] != "Pass":
                            vin_dict[item]['pm'] = 'No Data'
                        if float(pm_dict[fam][order][test]['ratio']) >= .9 and float(pm_dict[fam][order][test]['ratio']) <= 1:
                            vin_dict[item]['pm'] = 'Pass'
                        if float(pm_dict[fam][order][test]['ratio']) > 0 and float(pm_dict[fam][order][test]['ratio']) < .9 and vin_dict[item]['pm'] != "Pass":
                            vin_dict[item]['pm'] = "Fail"
                    except:
                        vin_dict[item]['pm'] = 'No Data'

for item in vin_dict:
    #If pass each criteria in any test Pass
    if vin_dict[item]['nox'] == 'Pass' and vin_dict[item]['co'] == 'Pass' and vin_dict[item]['pm'] == 'Pass':
        vin_dict[item]['all'] = 'Pass'
    #If Fail one criteria test fail
    elif vin_dict[item]['nox'] == 'Fail' or vin_dict[item]['co'] == 'Fail' or vin_dict[item]['pm'] == 'Fail':
        vin_dict[item]['all'] = 'Fail'
        print(item)
    #Else unknown
    else:
        vin_dict[item]['all'] = 'Unknown'

pass_count=0
for item in vin_dict:
    if vin_dict[item]['all'] == 'Pass':
        pass_count += 1
fail_count=0
for item in vin_dict:
    if vin_dict[item]['all'] == 'Fail':
        fail_count += 1
unknown_count=0
for item in vin_dict:
    if vin_dict[item]['all'] == 'Unknown':
        unknown_count += 1

print ('Pass:' + str(pass_count))
print ('Fail:' + str(fail_count))
print ('Unknown:' + str(unknown_count))

fcsv.write('Total VINs Passed, Total VINs Failed, Total VINs Unknown, Percentage VINs Passed, Percentage VINs Failed, Percentage VINs Unknown\n')
fcsv.write('%s,%s,%s,%s,%s,%s\n\n' % (pass_count,fail_count,unknown_count,(100*(pass_count/len(vin_dict))),(100*(fail_count/len(vin_dict))),(100 * (unknown_count/len(vin_dict)))))

fcsv.write('\nOverall Constituent Averages\n\n' + 'Nox Pass Average, Co Pass Average, PM Pass Average\n')
fcsv.write('%s,%s,%s\n\n' % (lst_mean(nox_pass_lst, decimal = 3),lst_mean(co_pass_lst, decimal = 3),lst_mean(pm_pass_lst, decimal = 3)))

fcsv.write('\nAt least one ratio > 1\n')
for item in bad_ratio:
    fcsv.write(item + " "+ '\n')

fcsv.close()
