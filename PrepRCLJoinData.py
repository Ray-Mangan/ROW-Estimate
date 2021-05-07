### PrepRCLJoinData
# Preps Row Summary table for RCL Join

# input parameters
in_RowSummary = arcpy.GetParameterAsText(0)

NOT_FLDS = ["MAXROW_BUF","MEANROW_BUF","MINROW_BUF"]

# Check for existence of specific fields - stop execution if they are found
flds = arcpy.ListFields(in_RowSummary)
delFields = []
for f in flds:
    if (f.name in NOT_FLDS):
        delFields.append(f.name)

if len(delFields) > 0:
    msg = "Please rename or delete fields {}" if len(delFields) > 1 else "Rename or delete field {}"
    arcpy.AddError(msg.format(delFields))
    sys.exit(0)

# Add new fields and calc them to 1/2 value of other fields
distFlds = [['MAXROW_BUF', 'DOUBLE'], 
     ['MINROW_BUF', 'DOUBLE'],
     ['MEANROW_BUF', 'DOUBLE']]
arcpy.management.AddFields(in_RowSummary,distFlds)
arcpy.AddMessage("Added fields to {}".format(in_RowSummary))

arcpy.management.CalculateFields(in_RowSummary, "PYTHON3", "MAXROW_BUF '!MAX_Shape_Length! * .5';MEANROW_BUF '!MEAN_Shape_Length! * .5';MINROW_BUF '!MIN_Shape_Length! * .5'", '')
arcpy.AddMessage("Calc'ed fields in {}".format(in_RowSummary))

arcpy.SetParameter(1,in_RowSummary)


