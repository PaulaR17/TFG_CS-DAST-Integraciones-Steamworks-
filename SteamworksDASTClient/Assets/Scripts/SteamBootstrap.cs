using UnityEngine;
using Steamworks;

public class SteamBootstrap : MonoBehaviour
{
    private bool steamInitialized = false;

    void Start()
    {
        if (!Packsize.Test())
        {
            Debug.LogError("[Steam] Packsize test failed. Wrong DLL architecture.");
            return;
        }

        if (!DllCheck.Test())
        {
            Debug.LogError("[Steam] DllCheck failed. Wrong Steamworks SDK version.");
            return;
        }

        try
        {
            steamInitialized = SteamAPI.Init();
        }
        catch (System.DllNotFoundException e)
        {
            Debug.LogError("[Steam] DLL not found: " + e);
            return;
        }

        if (!steamInitialized)
        {
            Debug.LogError("[Steam] SteamAPI.Init() failed. Is Steam running and logged in? Is steam_appid.txt set to 480?");
            return;
        }

        Debug.Log("[Steam] Initialized OK");
        Debug.Log("[Steam] SteamID: " + SteamUser.GetSteamID().ToString());
        Debug.Log("[Steam] Persona name: " + SteamFriends.GetPersonaName());
        Debug.Log("[Steam] AppID: " + SteamUtils.GetAppID().ToString());
    }

    void Update()
    {
        if (steamInitialized)
        {
            SteamAPI.RunCallbacks();
        }
    }

    void OnApplicationQuit()
    {
        if (steamInitialized)
        {
            SteamAPI.Shutdown();
        }
    }
}