
<#
.SYNOPSIS
Send the collected logs to the Elasticsearch.

.DESCRIPTION
This script is part of DetectLM. DetectLM is analyze and detects malicious commands
executed via cmd.exe with machine learning.

.EXAMPLE
C:\PS> powershell -exec bypass .\Invoke-DetectLM.ps1 -ehost 192.168.0.1

.NOTES
This script informs alert with popup window. If you have not executed command, click
"No" on popuped window.

.LINK
https://github.com/JPCERTCC/DetectLM

#>
Param(
   [string]
   $ehost,

   [int]
   $eport = 9200
)

$esCmd = @{ index = @{ _index = "cmdlogs"; _type = "command" ; _id = "" } }
$postdata = ''
$delim = ''
$hostname = hostname
$username = $env:username
$idlength = 10
$characters = 'abcdefghkmnprstuvwxyzABCDEFGHKLMNPRSTUVWXYZ123456789'
$Folderpath = $env:localappdata + '\CMDLogs'
$LogFolder = $PSScriptRoot + '\logs'
$ErrorFile = $LogFolder + '\error.log'
$StatusFilename = Get-Date -Format 'yyyyMMdd'
$StatusFile = $LogFolder + '\' + $StatusFilename + '.log'
$cStatusFile = $LogFolder + '\status.log'
$qJSON = '{"query": {"bool": {"must": [{"match": {"Hostname": "' + $hostname + '"}}, {"match": {"AlertLevel": 1}}, {"match": {"Ignore" : 0}}]}}}'


if(-Not(Test-Path $LogFolder))
{
    New-Item -path $PSScriptRoot -name logs -type directory
}

if(Test-Path $cStatusFile)
{
    $cStatus = $TRUE
    $cDatacsv = Get-Content $cStatusFile
} else {
    $cStatus = $FALSE
}

try{
    $uri_status = 'http://'+$ehost+':'+$eport+'/'
    $status = Invoke-WebRequest -Uri $uri_status -Method GET
} catch [Exception] {
    $eDate = Get-Date -Format G
    $eMessage = '[Warning] ' + $eDate + ' Server status check: ' + $Error[0]
    $eMessage | out-file -filepath $ErrorFile -Append;
}

foreach($file in Get-ChildItem -Name -Path $Folderpath -Filter *.log | Sort-Object)
{
    if($cStatus){
        if($file -ne $cDatacsv[0]){
            continue
        } else {
            $csv = Import-Csv $Folderpath\$file | Select-Object -Skip $cDatacsv[1]
            $cStatus = $FALSE
        }
    } else {
        $csv = Import-Csv $Folderpath\$file
    }
    $csv | ForEach-Object {
        $idrandom = 1..$idlength | ForEach-Object { Get-Random -Maximum $characters.length }
        $esCmd.index._id = [String]$characters[$idrandom] -replace " ", ""
        $postdata = $postdata + $delim + ($esCmd | ConvertTo-Json -Compress);
        $delim = "`n"
        $_ | Add-Member Hostname ($hostname)
        $_ | Add-Member Username ($username)
        $_ | Add-Member AlertLevel (0)
        $_ | Add-Member Ignore (0)
        $postdata = $postdata + $delim +($_ | ConvertTo-Json -Compress);
    }
}

if($postdata){
    try{
        $uri = 'http://'+$ehost+':'+$eport+'/_bulk'
        $postdata =Invoke-WebRequest -Uri $uri -Method POST -Body $postdata -ContentType 'application/json'
        $sDate = Get-Date -Format G
        $sMessage = '[Sucess] ' + $sDate + ' Push log Data: ' + $file
        $sMessage | out-file -filepath $StatusFile -Append;

        $file | out-file -filepath $cStatusFile
        $csv.count + $cDatacsv[1] | out-file -filepath $cStatusFile -Append
    } catch [Exception] {
        $eDate = Get-Date -Format G
        $eMessage = '[Warning] ' + $eDate + ' Push log Data: ' + $Error[0]
        $eMessage | out-file -filepath $ErrorFile -Append;
    }
}

try{
    $uri = 'http://'+$ehost+':'+$eport+'/cmdlogs/command/_search?pretty'
    $postdata =Invoke-WebRequest -Uri $uri -Method POST -Body $qJSON -ContentType 'application/json'
    #Write-Host $postdata

    $sDate = Get-Date -Format G
    $sMessage = '[Sucess] ' + $sDate + ' Get Elasticsearch Data'
    $sMessage | out-file -filepath $StatusFile -Append;
    $conStatus = $TRUE
} catch [Exception] {
    $eDate = Get-Date -Format G
    $eMessage = '[Warning] ' + $eDate + ' Get Elasticsearch Data: ' + $Error[0]
    $eMessage | out-file -filepath $ErrorFile -Append;
    $conStatus = $FALSE
}

$sdata  = $postdata | ConvertFrom-Json
if(($sdata.hits.total -ne 0) -And $conStatus){
    $cadata = $sdata.hits.hits._source.command
    $tadata = $sdata.hits.hits._source.timestamp
    $i = 0
    foreach($aCommand in $cadata){
        $CommandList = $CommandList + $tadata[$i] + ' | '
        $CommandList = $CommandList + $aCommand + "`r`n"
        $i += 1
    }
    #$aCommand = $dtdata -join "`r`n"
    $wsobj = new-object -ComObject Wscript.Shell -ErrorAction Stop
    $uResult = $wsobj.popup("Did you run the following commands?`r`n`r`n" + $CommandList,0,'Command Execution Alart',48+4)

    $uri = 'http://'+$ehost+':'+$eport+'/cmdlogs/command/'

    if($uResult -eq 6){
        $sDate = Get-Date -Format G
        $sMessage = '[Sucess] ' + $sDate + ' Alert action: Yes'
        $sMessage | out-file -filepath $StatusFile -Append;

        $cJSON = '{"script" : "ctx._source.Ignore=1"}'
    } elseif($uResult -eq 7){
        $sDate = Get-Date -Format G
        $sMessage = '[Sucess] ' + $sDate + ' Alert action: No'
        $sMessage | out-file -filepath $StatusFile -Append;

        $cJSON = '{"script" : "ctx._source.AlertLevel=2"}'
    }

    $gid = $sdata.hits.hits._id
    foreach($id in $gid){
        $curi = $uri + $id + '/_update?pretty'
        try{
            $postdata =Invoke-WebRequest -Uri $curi -Method POST -Body $cJSON -ContentType 'application/json'

            $sDate = Get-Date -Format G
            $sMessage = '[Sucess] ' + $sDate + ' Change Data Flag'
            $sMessage | out-file -filepath $StatusFile -Append;
        } catch [Exception] {
            $eDate = Get-Date -Format G
            $eMessage = '[Warning] ' + $eDate + ' Change Data Flag: ' + $Error[0]
            $eMessage | out-file -filepath $ErrorFile -Append;
        }
    }
}
Get-ChildItem $LogFolder -Recurse | Where-object{((Get-Date)-$_.LastWriteTime).Days -gt 30} | foreach-object { $_.Delete() }
