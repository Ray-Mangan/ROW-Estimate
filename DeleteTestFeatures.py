in_features = arcpy.GetParameter(0)
for f in in_features:
    try:
        desc = arcpy.Describe(f)
        delpath = desc.catalogPath
        arcpy.management.Delete(delpath)
        arcpy.AddMessage("Deleted {}".format(delpath))
    except:
        e1=sys.exc_info()[1]
        arcpy.AddWarning("An error occurred while deleting {}: {}".format(f,e1))


arcpy.SetParameterAsText(1,True)
