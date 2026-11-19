@echo off
rem ============================================================================
rem  Installation de l'assistant du meneur (Metal Adventures 1.5) sous Windows.
rem  Double-cliquez sur ce fichier. Il peut être relancé sans risque.
rem    1. installe uv (outil qui installe Python et les bibliothèques) s'il manque ;
rem    2. installe Python et les bibliothèques du projet (uv sync) ;
rem    3. crée secrets.yaml à partir de secrets.exemple.yaml s'il n'existe pas ;
rem    4. affiche ce qu'il reste à faire pour commencer.
rem ============================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo === Installation de l'assistant du meneur ===
echo Dossier du projet : %CD%
echo.

rem --- 1. uv -------------------------------------------------------------------
rem L'installateur officiel place uv dans %USERPROFILE%\.local\bin : on l'ajoute
rem au chemin de cette fenêtre, car Windows ne le voit qu'au prochain terminal.
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

where uv >nul 2>nul
if not errorlevel 1 goto uv_present

echo [1/3] Installation de uv : téléchargement depuis astral.sh...
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
where uv >nul 2>nul
if errorlevel 1 goto echec_uv
goto uv_ok

:uv_present
echo [1/3] uv est déjà installé.

:uv_ok
uv --version
echo.

rem --- 2. Python et bibliothèques ----------------------------------------------
echo [2/3] Installation de Python et des bibliothèques : uv sync...
echo       La première fois, le téléchargement peut prendre quelques minutes.
uv sync
if errorlevel 1 goto echec_sync
echo.

rem --- 3. Fichier des clés -----------------------------------------------------
if exist "secrets.yaml" goto secrets_present
copy "secrets.exemple.yaml" "secrets.yaml" >nul
if errorlevel 1 goto echec_secrets
echo [3/3] Fichier secrets.yaml créé à partir du modèle : il reste à y mettre vos clés.
goto suite

:secrets_present
echo [3/3] secrets.yaml existe déjà : il n'a pas été modifié.

:suite
echo.
echo ============================================================================
echo  Installation terminée.
echo ============================================================================
echo.
echo  Pour commencer :
echo.
echo   1. Ouvrez un terminal dans le dossier du projet :
echo      dans l'Explorateur, ouvrez le dossier, cliquez dans la barre d'adresse,
echo      tapez cmd puis appuyez sur Entrée.
echo.
echo   2. Démarrez l'interface web en tapant :
echo.
echo        uv run web
echo.
echo      Le navigateur s'ouvre sur http://127.0.0.1:8000
echo      Pour arrêter : Ctrl+C dans le terminal.
echo.
echo   3. Dans l'interface, bouton engrenage ⚙ en haut à droite : collez votre clé API.
echo      Ou bien ouvrez secrets.yaml avec le Bloc-notes. Voir MANUEL.md, section 4.
echo.
echo   4. Onglet Livres : ajoutez vos deux PDF de Metal Adventures 1.5.
echo      Voir MANUEL.md, section 5.
echo.
echo  L'aide complète est dans l'interface web, bouton ?.
echo.
pause
exit /b 0

:echec_uv
echo.
echo ERREUR : uv n'a pas pu être installé.
echo Vérifiez votre connexion Internet, puis relancez ce fichier.
echo Si l'erreur persiste, voir MANUEL.md, section 3.
echo.
pause
exit /b 1

:echec_sync
echo.
echo ERREUR : l'installation de Python ou des bibliothèques a échoué.
echo Lisez le message ci-dessus, vérifiez votre connexion Internet, puis relancez ce fichier.
echo.
pause
exit /b 1

:echec_secrets
echo.
echo ERREUR : impossible de créer secrets.yaml à partir de secrets.exemple.yaml.
echo Vérifiez que secrets.exemple.yaml est bien dans le dossier du projet.
echo.
pause
exit /b 1
