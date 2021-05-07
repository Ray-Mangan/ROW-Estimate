### ClipByProcessingBins.py
# 

def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))


### inputs
in_parcels = arcpy.GetParameterAsText(0)
in_rcls = arcpy.GetParameterAsText(1)
in_bins = arcpy.GetParameterAsText(2)

### fetch oids from bins for makefeaturelayer :{
fields=['OID@']
bins = []
with arcpy.da.SearchCursor(in_bins, fields) as cursor:
    for row in cursor:
        bins.append(row[0])

x = 3
for b in bins:
    where = "objectid = {}".format(b)    
    lyrName = "bin_{}".format(b)
    #arcpy.AddMessage("{} - {}".format(lyrName, where))

    result = arcpy.management.MakeFeatureLayer(in_bins,lyrName,where)
    lyr = result.getOutput(0)
    
    clippedParname = "{}_parcel".format(lyrName)
    clippedRCLname = "{}_rcl".format(lyrName)

    result = arcpy.analysis.Clip(in_parcels, lyr, clippedParname, None)
    getMsgs("Parcel Clip: ")
    result = arcpy.analysis.Clip(in_rcls, lyr, clippedRCLname, None)
    getMsgs("RCL Clip: ")

    arcpy.SetParameter(x,lyr)
    x+=1

    
    

##
##
##### Near parcels to RCLs
##arcpy.analysis.Near(in_parcels, in_rcls, None, "LOCATION", "NO_ANGLE", "PLANAR", "NEAR_FID NEAR_FID;NEAR_DIST NEAR_DIST;NEAR_X NEAR_X;NEAR_Y NEAR_Y")
##getMsgs("Near {} to {}".format(in_parcels, in_rcls))
##
##### Generate points from the near xy values in parcels
##result = arcpy.management.MakeXYEventLayer(in_parcels, "NEAR_X", "NEAR_Y", "NearPoints_From_Parcels", "PROJCS['NAD_1983_HARN_StatePlane_Hawaii_3_FIPS_5103_Feet',GEOGCS['GCS_North_American_1983_HARN',DATUM['D_North_American_1983_HARN',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',1640416.666666667],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-158.0],PARAMETER['Scale_Factor',0.99999],PARAMETER['Latitude_Of_Origin',21.16666666666667],UNIT['Foot_US',0.3048006096012192]];-16807900 -40496900 3048.00609601219;-100000 10000;-100000 10000;3.28083333333333E-03;0.001;0.001;IsHighPrecision", None)
##getMsgs("MakeXYEventLayer {}".format(in_parcels))
##nearPntsFromParcels = result.getOutput(0)
##result = arcpy.management.CopyFeatures(nearPntsFromParcels, out_distRowPnts, '', None, None, None)
##distROWpnts = result.getOutput(0)
##getMsgs("CopyFeatures {} to {}".format(nearPntsFromParcels, distROWpnts))
##
##### near output points to parcels 
##arcpy.analysis.Near(distROWpnts, in_parcels, None, "LOCATION", "NO_ANGLE", "PLANAR", "NEAR_FID NEAR_FID_Parcel;NEAR_DIST NEAR_DIST_Parcel;NEAR_X NEAR_X_Parcel;NEAR_Y NEAR_Y_Parcel")
##getMsgs("Near {} to {}".format(distROWpnts, in_parcels))
##
##### join field back to RCLs to get SegmentID
##arcpy.management.JoinField(distROWpnts, "NEAR_FID", in_rcls, "OBJECTID", "SEGMENTID")
##
#### generate two feature layers from distROWpnts
##where1 = "NEAR_DIST > 0 and NEAR_DIST_Parcel > 0"
##result = arcpy.management.MakeFeatureLayer(distROWpnts, "NearFeatures", where1)
##nearFeatures = result.getOutput(0)
##
##where2 = "NEAR_DIST <= 0 OR NEAR_DIST_Parcel <= 0"
##result = arcpy.management.MakeFeatureLayer(distROWpnts, "InvalidDistanceFeatures", where2, None, "OBJECTID_1 OBJECTID_1 VISIBLE NONE;Shape Shape VISIBLE NONE;OBJECTID OBJECTID HIDDEN NONE;PARCEL_UID PARCEL_UID HIDDEN NONE;TYPE TYPE HIDDEN NONE;TMK TMK HIDDEN NONE;TAXPIN TAXPIN HIDDEN NONE;REC_AREA_A REC_AREA_A HIDDEN NONE;REC_AREA_S REC_AREA_S HIDDEN NONE;STREET_PAR STREET_PAR VISIBLE NONE;FLOATING_P FLOATING_P HIDDEN NONE;ZSP ZSP HIDDEN NONE;TMK8NUM TMK8NUM HIDDEN NONE;TMK9NUM TMK9NUM HIDDEN NONE;IN_DATE IN_DATE HIDDEN NONE;IN_FILE_NU IN_FILE_NU HIDDEN NONE;IN_EDIT_EV IN_EDIT_EV HIDDEN NONE;NHOOD_NUM NHOOD_NUM HIDDEN NONE;LOADDATE LOADDATE HIDDEN NONE;NEAR_FID NEAR_FID VISIBLE NONE;NEAR_DIST NEAR_DIST VISIBLE NONE;NEAR_X NEAR_X VISIBLE NONE;NEAR_Y NEAR_Y VISIBLE NONE;NEAR_FID_Parcel NEAR_FID_Parcel VISIBLE NONE;NEAR_DIST_Parcel NEAR_DIST_Parcel VISIBLE NONE;NEAR_X_Parcel NEAR_X_Parcel VISIBLE NONE;NEAR_Y_Parcel NEAR_Y_Parcel VISIBLE NONE")
##invalidDistFeatures = result.getOutput(0)
##
##arcpy.SetParameterAsText(2, distROWpnts)
##arcpy.SetParameterAsText(3, nearFeatures)
##arcpy.SetParameterAsText(4, invalidDistFeatures)
