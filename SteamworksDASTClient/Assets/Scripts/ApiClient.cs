using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

public class ApiClient : MonoBehaviour
{
    public static ApiClient Instance { get; private set; }

    [Header("Backend")]
    [Tooltip("Backend del lab. Ej: http://192.168.0.103:8080 o http://192.168.0.103:8080")]
    public string baseUrl = "http://192.168.0.103:8080";

    public string AccessToken { get; private set; }
    public string UserId { get; private set; }
    public string Username { get; private set; }
    public int Credits { get; private set; }

    void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
    }

    // ---------- AUTH ------------
    [Serializable]
    private class SteamLoginReq
    {
        public string steam_id;
        public string persona_name;
    }

    [Serializable]
    private class LoginRes
    {
        public string access_token;
        public string user_id;
        public string username;
        public string steam_id;
        public int credits;
    }

    public void SteamLogin(string steamId, string personaName, Action onSuccess, Action<string> onError)
    {
        var body = JsonUtility.ToJson(new SteamLoginReq { steam_id = steamId, persona_name = personaName });
        StartCoroutine(PostJson("/auth/steam_login", body, false, (json) =>
        {
            var res = JsonUtility.FromJson<LoginRes>(json);
            AccessToken = res.access_token;
            UserId = res.user_id;
            Username = res.username;
            Credits = res.credits;
            Debug.Log($"[API] Login OK user={Username} credits={Credits}");
            onSuccess?.Invoke();
        }, onError));
    }

    // ---------- USERS ----------
    [Serializable]
    private class UserRes
    {
        public string id;
        public string steam_id;
        public string username;
        public int credits;
        public bool is_admin;
    }

    public void GetUserMe(Action<int> onSuccess, Action<string> onError)
    {
        StartCoroutine(GetJson("/users/me", true, (json) =>
        {
            var res = JsonUtility.FromJson<UserRes>(json);
            Credits = res.credits;
            onSuccess?.Invoke(res.credits);
        }, onError));
    }

    // ---------- INVENTORY ----------
    [Serializable] private class AddItemReq { public string item_name; public string quality; }

    public void AddItemToInventory(string itemName, string quality,
                                   Action onSuccess, Action<string> onError)
    {
        var body = JsonUtility.ToJson(new AddItemReq { item_name = itemName, quality = quality });
        StartCoroutine(PostJson("/inventory/me/items", body, true,
            (json) => { Debug.Log($"[API] Item added: {itemName}"); onSuccess?.Invoke(); },
            onError));
    }

    // ---------- ACHIEVEMENTS ----------
    [Serializable] private class UnlockReq { public string achievement_code; } // <-- Cambio aquí

    public void UnlockAchievement(string achievementCode, Action onSuccess, Action<string> onError)
    {
        // <-- Cambio aquí abajo también
        var body = JsonUtility.ToJson(new UnlockReq { achievement_code = achievementCode });
        StartCoroutine(PostJson("/achievements/unlock", body, true,
            (json) => { Debug.Log($"[API] Achievement unlocked: {achievementCode}"); onSuccess?.Invoke(); },
            onError));
    }

    // ---------- CLOUD SAVE ----------
    [Serializable] private class CloudSaveReq { public string slot_name; public string save_data; }

    public void CloudSave(string saveData, Action onSuccess, Action<string> onError)
    {
        var body = JsonUtility.ToJson(new CloudSaveReq { slot_name = "slot1", save_data = saveData });
        StartCoroutine(PostJson("/cloud/save", body, true,
            (json) => { Debug.Log("[API] Cloud save OK"); onSuccess?.Invoke(); },
            onError));
    }

    // ---------- TRANSACTIONS ----------
    [Serializable] private class InitTxReq { public string order_id; public string item_name; public int amount; } // <-- Añadido order_id
    [Serializable] private class InitTxRes { public string id; public string order_id; }
    [Serializable] private class FinalizeTxReq { public string order_id; public bool approved_by_client; }

    public void InitTransaction(string itemName, int amount,
                                Action<string> onSuccess, Action<string> onError)
    {
        // Generamos el ID de la orden en el cliente, igual que hacías antes
        string generatedOrderId = "BUY_" + System.DateTime.Now.Ticks;

        // Lo metemos en el JSON
        var body = JsonUtility.ToJson(new InitTxReq { order_id = generatedOrderId, item_name = itemName, amount = amount });

        StartCoroutine(PostJson("/transactions/init", body, true, (json) =>
        {
            var res = JsonUtility.FromJson<InitTxRes>(json);
            Debug.Log($"[API] Tx init order_id={res.order_id}");
            onSuccess?.Invoke(res.order_id);
        }, onError));
    }

    // OJO: usamos el endpoint VULNERABLE a propósito (cliente "ingenuo").
    // Esto es coherente con el TFG: el atacante en W2 explota el mismo endpoint.
    public void FinalizeTransaction(string orderId, Action onSuccess, Action<string> onError)
    {
        var body = JsonUtility.ToJson(new FinalizeTxReq { order_id = orderId, approved_by_client = true });
        StartCoroutine(PostJson("/vulnerable/transactions/finalize", body, true,
            (json) => { Debug.Log("[API] Tx finalize OK"); onSuccess?.Invoke(); },
            onError));
    }

    // ---------- HTTP HELPERS ----------
    private IEnumerator PostJson(string path, string jsonBody, bool useAuth,
                                 Action<string> onSuccess, Action<string> onError)
    {
        using (var req = new UnityWebRequest(baseUrl + path, "POST"))
        {
            byte[] raw = Encoding.UTF8.GetBytes(jsonBody);
            req.uploadHandler = new UploadHandlerRaw(raw);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            if (useAuth && !string.IsNullOrEmpty(AccessToken))
                req.SetRequestHeader("Authorization", "Bearer " + AccessToken);

            yield return req.SendWebRequest();

            if (req.result == UnityWebRequest.Result.Success)
                onSuccess?.Invoke(req.downloadHandler.text);
            else
                onError?.Invoke($"{req.responseCode} {req.error} :: {req.downloadHandler.text}");
        }
    }

    private IEnumerator GetJson(string path, bool useAuth,
                                Action<string> onSuccess, Action<string> onError)
    {
        using (var req = UnityWebRequest.Get(baseUrl + path))
        {
            if (useAuth && !string.IsNullOrEmpty(AccessToken))
                req.SetRequestHeader("Authorization", "Bearer " + AccessToken);

            yield return req.SendWebRequest();

            if (req.result == UnityWebRequest.Result.Success)
                onSuccess?.Invoke(req.downloadHandler.text);
            else
                onError?.Invoke($"{req.responseCode} {req.error} :: {req.downloadHandler.text}");
        }
    }
}