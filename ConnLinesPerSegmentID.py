inConLines = arcpy.GetParameterAsText(0)
inRcls = arcpy.GetParameterAsText(1)
namePrefix = arcpy.GetParameterAsText(2)

# filter out review connection lines
where = "REVIEW <> 1"
result = arcpy.management.MakeTableView(inConLines,"{}_ConLineNoReview",where)
filteredConLines = result.getOutput(0)

# Run frequency to derive the total number of connection lines per segmentID
outName = "{}_ConLineFrequency".format(namePrefix)
result = arcpy.analysis.Frequency(filteredConLines, outName, "SEGMENTID", None)
conTbl = result.getOutput(0)

# JoinField the output frequency table (conTbl) to RCLs to get the length of the original RCL
arcpy.management.JoinField(conTbl, "SEGMENTID", inRcls, "SEGMENTID", "Shape_Length")

# Add a field and calc it to derive the estimated distance between connection lines along an RCL
arcpy.management.AddField(conTbl, "NumCons", "LONG", None, None, None, '', "NULLABLE", "NON_REQUIRED", '')
arcpy.management.CalculateField(conTbl, "NumCons", "!Shape_Length! / !FREQUENCY!", "PYTHON3", '', "TEXT")

# Get count
where = "NumCons > 150"
tbViewName = "{}_view".format(conTbl)
result = arcpy.management.MakeTableView(conTbl,tbViewName,where)
tbViewNameout = result.getOutput(0)
result = arcpy.management.GetCount(tbViewNameout)
cnt = int(result.getOutput(0))
arcpy.AddMessage("Number of segmentIDs with connection line spacing exceeding 150' = {}".format(cnt))

arcpy.SetParameter(3,conTbl)