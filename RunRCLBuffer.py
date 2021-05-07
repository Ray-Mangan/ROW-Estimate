# input parameters
in_RCLs = arcpy.GetParameterAsText(0)

### Buffers 3x by the each ROW distance field
result = arcpy.analysis.Buffer(in_RCLs, "in_memory\\MAXROW_BUF", "MAXROW_BUF", "FULL", "FLAT", "NONE", None, "PLANAR")
arcpy.AddMessage("Buffered {} by MAXROW_BUF".format(in_RCLs))
arcpy.SetParameter(1,result.getOutput(0))

result = arcpy.analysis.Buffer(in_RCLs, "in_memory\\MEANROW_BUF", "MEANROW_BUF", "FULL", "FLAT", "NONE", None, "PLANAR")
arcpy.AddMessage("Buffered {} by MEANROW".format(in_RCLs))
arcpy.SetParameter(2,result.getOutput(0))

result = arcpy.analysis.Buffer(in_RCLs, "in_memory\\MINROW_BUF", "MINROW_BUF", "FULL", "FLAT", "NONE", None, "PLANAR")
arcpy.AddMessage("Buffered {} by MINROW".format(in_RCLs))
arcpy.SetParameter(3,result.getOutput(0))


