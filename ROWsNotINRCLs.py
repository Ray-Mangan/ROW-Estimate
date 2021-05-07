def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))


inROWS = arcpy.GetParameter(0)
inRCLs = arcpy.GetParameterAsText(1)
namePrefix = arcpy.GetParameterAsText(2)

ROWS = []
rcls = []

for t in inROWS:
	fields = ["SEGMENTID"]
	with arcpy.da.SearchCursor(t, fields) as cursor:
	    for row in cursor:
	    	ROWS.append(int(row[0]))
	
	arcpy.AddMessage("{} has {} rows".format(t,len(ROWS)))


rowSet = set(ROWS)
arcpy.AddMessage("rowSet has {} rows".format(len(rowSet)))

fields = ["SEGMENTID"]
with arcpy.da.SearchCursor(inRCLs, fields) as cursor1:
    for row1 in cursor1:
    	rcls.append(int(row1[0]))

arcpy.AddMessage("{} has {} rows".format(inRCLs,len(rcls)))

where = ""
cnt = 0
notcnt = 0
for r in rcls:
	if r in rowSet:
		cnt += 1
	else:
		notcnt += 1
		if len(where) < 1:
			where = "{},".format(r)
		else:
			where += ",{}".format(r)

where = where.replace(',,',',')
if where.endswith(','):
    where = where[0:len(where)-1]
    
arcpy.AddMessage("in condition = {}".format(cnt))
arcpy.AddMessage("not in condition = {}".format(notcnt))
arcpy.AddMessage("Where clause = {}".format(where))
where = "SEGMENTID in ({})".format(where)

outLyrName = "{}_RCLs_with_no_ROW_value".format(namePrefix)
result = arcpy.management.MakeFeatureLayer(inRCLs, outLyrName, where)
rclsWithNoSummary = result.getOutput(0)
arcpy.SetParameterAsText(3, rclsWithNoSummary)

result = arcpy.management.GetCount(rclsWithNoSummary)
arcpy.AddMessage("{} rowcount = {}".format(rclsWithNoSummary,result.getOutput(0)))
