; WhisperGUI - NSIS installer (per-user, senza admin)
Unicode true

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WordFunc.nsh"

!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef APP_PATH
  !define APP_PATH "..\..\dist\WhisperGUI"
!endif
!ifndef OUT_FILE
  !define OUT_FILE "WhisperGUI-x86_64-setup.exe"
!endif

!define APP_NAME "WhisperGUI"
!define APP_EXE "WhisperGUI.exe"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\WhisperGUI"
; HWND_BROADCAST e' gia' definito da NSIS 3.x: guardia per evitare redefine
!ifndef HWND_BROADCAST
  !define HWND_BROADCAST 0xFFFF
!endif
!ifndef WM_SETTINGCHANGE
  !define WM_SETTINGCHANGE 0x001A
!endif

Name "${APP_NAME}"
OutFile "${OUT_FILE}"
InstallDir "$LOCALAPPDATA\WhisperGUI"
RequestExecutionLevel user
CRCCheck on

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
Page custom AddPathPage AddPathLeave
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Italian"

Var PATH_CHECKBOX

Function AddPathPage
  !insertmacro MUI_HEADER_TEXT "Opzioni" "Opzioni aggiuntive"
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0 0 100% 24u "Rende disponibile 'whisper-gui' come comando da terminale."
  Pop $0
  ${NSD_CreateCheckbox} 0 28u 100% 12u "Aggiungi WhisperGUI al PATH utente" PATH_CHECKBOX
  Pop $PATH_CHECKBOX
  nsDialogs::Show
FunctionEnd

Function AddPathLeave
  ${NSD_GetState} $PATH_CHECKBOX $0
  ${If} $0 <> 0
    ReadRegStr $1 HKCU "Environment" "Path"
    ${WordFind} "$1" "$INSTDIR" "+1" $2
    ${If} ${Errors}
      StrCpy $2 "$1;$INSTDIR"
      WriteRegExpandStr HKCU "Environment" "Path" "$2"
      SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
    ${EndIf}
  ${EndIf}
FunctionEnd

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "${APP_PATH}\*.*"

  WriteUninstaller "$INSTDIR\uninstall.exe"

  CreateDirectory "$SMPROGRAMS\WhisperGUI"
  CreateShortcut "$SMPROGRAMS\WhisperGUI\WhisperGUI.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\WhisperGUI\Disinstalla WhisperGUI.lnk" "$INSTDIR\uninstall.exe"

  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "WhisperGUI"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
SectionEnd

Section "Uninstall"
  RMDir /r "$INSTDIR"
  RMDir /r "$SMPROGRAMS\WhisperGUI"
  DeleteRegKey HKCU "${UNINST_KEY}"
SectionEnd
