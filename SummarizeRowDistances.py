def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))

inConnectionLines = arcpy.GetParameterAsText(0)
where = arcpy.GetParameterAsText(1)
namePrefix = arcpy.GetParameterAsText(2)

## filter using the where clause
result = arcpy.management.MakeFeatureLayer(inConnectionLines,"{}_summaryLayer",where)
tbl = result.getOutput(0)
getMsgs("Filtered {} by {}".format(inConnectionLines,where))

### Summarize ROW distances
result = arcpy.analysis.Statistics(tbl, "in_memory\\{}_ROWSummary".format(namePrefix), "Shape_Length MAX;Shape_Length MIN;Shape_Length MEAN", "SEGMENTID")
outSummary = result.getOutput(0)
getMsgs("Run Summary Stats on {} and create".format(tbl,outSummary))

arcpy.SetParameter(3, outSummary)
