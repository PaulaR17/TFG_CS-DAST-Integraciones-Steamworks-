using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using Steamworks;

public class ApiClient : MonoBehaviour
{
    [Header("Backend (apunta a mitmproxy reverse, no al API directo)")]
    public string backendBaseUrl = "http://192.168.0.103:8080";

    private string accessToken = null;
    private string userId = null;

    public bool IsLoggedIn => !string.IsNullOrEmpty(accessToken);
    public string CurrentUserId => userId;
    ------------------------------------------------------------------
    public void DoLogin() => StartCoroutine(LoginCoroutine());
    public void DoGetMyProfile() => StartCoroutine(GetCoroutine("/users/me"));

    public void DoGetMyInventory()
    {
        if (!IsLoggedIn) { Debug.LogWarning("[Api] Login first"); return; }
        StartCoroutine(GetCoroutine("/vulnerable/inventory/" + userId));
    }

    public void DoUnlockAchievement(string achievementCode)
    {
        StartCoroutine(PostCoroutine("/achievements/unlock",
            "{\"achievement_code\":\"" + achievementCode + "\"}"));
    }

    public void DoCloudSave(string saveData)
    {
        // Escape manual de comillas en saveData
        string escapedSaveData = saveData.Replace("\\", "\\\\").Replace("\"", "\\\"");
        string body = "{\"slot_name\":\"slot1\",\"save_data\":\"" + escapedSaveData + "\"}";
        StartCoroutine(PostCoroutine("/cloud/save", body));
    }

    public void DoBuyItem(string itemName, int amount)
    {
        StartCoroutine(BuyItemCoroutine(itemName, amount));
    }

    private IEnumerator LoginCoroutine()
    {
        if (!SteamAPI.IsSteamRunning())
        {
            Debug.LogError("[Api] Steam not running");
            yield break;
        }

        CSteamID steamId = SteamUser.GetSteamID();
        string body = "{\"steam_id\":\"" + steamId.ToString() +
                      "\",\"persona_name\":\"" + SteamFriends.GetPersonaName() + "\"}";

        UnityWebRequest req = new UnityWebRequest(backendBaseUrl + "/auth/steam_login", "POST");
        req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("[Api] Login failed: " + req.error + " | " + req.downloadHandler.text);
            yield break;
        }

        Debug.Log("[Api] Login response: " + req.downloadHandler.text);
        var resp = JsonUtility.FromJson<LoginResponse>(req.downloadHandler.text);
        accessToken = resp.access_token;
        userId = resp.user_id;
        Debug.Log("[Api] Logged in. user_id=" + userId);
    }

    private IEnumerator GetCoroutine(string path)
    {
        UnityWebRequest req = UnityWebRequest.Get(backendBaseUrl + path);
        if (IsLoggedIn) req.SetRequestHeader("Authorization", "Bearer " + accessToken);
        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("[Api] GET " + path + " failed: " + req.error);
            yield break;
        }
        Debug.Log("[Api] GET " + path + " -> " + req.downloadHandler.text);
    }

    private IEnumerator PostCoroutine(string path, string body)
    {
        UnityWebRequest req = new UnityWebRequest(backendBaseUrl + path, "POST");
        req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        if (IsLoggedIn) req.SetRequestHeader("Authorization", "Bearer " + accessToken);

        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("[Api] POST " + path + " failed: " + req.error + " | " + req.downloadHandler.text);
            yield break;
        }
        Debug.Log("[Api] POST " + path + " -> " + req.downloadHandler.text);
    }

    private IEnumerator BuyItemCoroutine(string itemName, int amount)
    {
        // Generamos UN solo order_id y lo reutilizamos en init y finalize
        string orderId = "BUY_" + System.DateTime.Now.Ticks;

        string initBody = "{\"order_id\":\"" + orderId +
                          "\",\"item_name\":\"" + itemName +
                          "\",\"amount\":" + amount + "}";
        yield return PostCoroutine("/transactions/init", initBody);

        string finalizeBody = "{\"order_id\":\"" + orderId +
                              "\",\"approved_by_client\":true}";
        yield return PostCoroutine("/vulnerable/transactions/finalize", finalizeBody);
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1)) DoLogin();
        if (Input.GetKeyDown(KeyCode.Alpha2)) DoGetMyProfile();
        if (Input.GetKeyDown(KeyCode.Alpha3)) DoGetMyInventory();
        if (Input.GetKeyDown(KeyCode.Alpha4)) DoUnlockAchievement("ACH_FIRST_LOGIN");
        if (Input.GetKeyDown(KeyCode.Alpha5)) DoCloudSave("level=1,score=0");
        if (Input.GetKeyDown(KeyCode.Alpha6)) DoBuyItem("Dragon Knife", 500);
    }

    [Serializable]
    private class LoginResponse
    {
        public string access_token;
        public string user_id;
    }
}