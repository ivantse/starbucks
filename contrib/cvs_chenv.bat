@set CVSROOT=%1
@set CVS_RSH=contrib\TortoiseCVS\TortoisePlink.exe
@set PLINK_PROTOCOL=ssh
@contrib\TortoiseCVS\cvs.exe %2 %3 %4 %5 %6 %7 %8
