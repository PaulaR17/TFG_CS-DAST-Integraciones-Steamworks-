using UnityEngine;
using TMPro;
using Steamworks;
using UnityEngine.SceneManagement;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    [Header("UI")]
    public TMP_Text scoreText;
    public TMP_Text creditsText;
    public TMP_Text healthText;
    public GameObject shopPanel;
    public GameObject gameOverPanel;
    public TMP_Text finalScoreText;
    public UnityEngine.UI.Button restartButton;
    public UnityEngine.UI.Button mainMenuButton;

    [Header("Player")]
    public GameObject player;

    [Header("Rewards")]
    [Tooltip("Cuantos credits gana el jugador por cada enemigo eliminado.")]
    public int creditsPerKill = 5;

    private int score = 0;
    private int health = 3;
    private bool achievement100Unlocked = false;
    private bool isGameOver = false;

    void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
    }

    void Start()
    {
        shopPanel.SetActive(false);
        gameOverPanel.SetActive(false);
        UpdateHUD();

        // Obtenemos el SteamID y el nombre del jugador directamente de Steamworks
        string steamId = SteamUser.GetSteamID().ToString();
        string personaName = SteamFriends.GetPersonaName();

        // Enviamos ambos par�metros al backend
        ApiClient.Instance.SteamLogin(steamId, personaName,
            onSuccess: () =>
            {
                Debug.Log("[GM] Login OK, refrescando perfil");
                ApiClient.Instance.GetUserMe(
                    (credits) => UpdateHUD(),
                    (err) => Debug.LogError("[GM] GetUserMe error: " + err));
            },
            onError: (err) => Debug.LogError("[GM] Login error: " + err));

        if (restartButton != null)
            restartButton.onClick.AddListener(OnRestart);
        if (mainMenuButton != null)
            mainMenuButton.onClick.AddListener(OnBackToMenu);
    }

    public void OnRestart()
    {
        Debug.Log("[GM] Reiniciando partida...");
        SceneManager.LoadScene(SceneManager.GetActiveScene().name);
    }

    public void OnBackToMenu()
    {
        Debug.Log("[GM] Volviendo al men�...");
        SceneManager.LoadScene("MainMenu");
    }

    public void AddScore(int amount)
    {
        if (isGameOver) return;
        score += amount;

        // Recompensa de credits por kill (feedback inmediato, sin llamar al backend).
        // El saldo persistente del backend se actualiza solo en login/purchase.
        if (ApiClient.Instance != null && creditsPerKill > 0)
            ApiClient.Instance.AddLocalCredits(creditsPerKill);

        UpdateHUD();

        if (!achievement100Unlocked && score >= 100)
        {
            achievement100Unlocked = true;
            ApiClient.Instance.UnlockAchievement("FIRST_100_POINTS",
                () => Debug.Log("[GM] Logro desbloqueado"),
                (err) => Debug.LogError("[GM] Achievement error: " + err));
        }
    }

    public void OnPickupPowerUp(string itemName, string quality)
    {
        ApiClient.Instance.AddItemToInventory(itemName, quality,
            () => Debug.Log("[GM] Item a�adido al inventario"),
            (err) => Debug.LogError("[GM] AddItem error: " + err));
    }

    public void TakeDamage()
    {
        if (isGameOver) return;
        health--;
        UpdateHUD();
        if (health <= 0) GameOver();
    }

    public void GameOver()
    {
        isGameOver = true;
        if (player != null) player.SetActive(false);

        string saveData = $"{{\"score\":{score},\"username\":\"{ApiClient.Instance.Username}\"}}";
        ApiClient.Instance.CloudSave(saveData,
            () => Debug.Log("[GM] Save subido a la nube"),
            (err) => Debug.LogError("[GM] CloudSave error: " + err));

        finalScoreText.text = $"Score: {score}";
        gameOverPanel.SetActive(true);
    }

    public void ToggleShop()
    {
        shopPanel.SetActive(!shopPanel.activeSelf);
    }

    public void OnPurchaseSuccess(int cost)
    {
        // OJO: el backend /vulnerable/transactions/finalize es la vulnerabilidad
        // intencionada del TFG: al confiar en approved_by_client=true, en lugar
        // de descontar credits, los SUMA al usuario. Para que el HUD refleje
        // la misma logica vulnerable del backend (y para no perder los credits
        // que el jugador ha ganado matando enemigos), sumamos localmente
        // sin volver a hacer GetUserMe.
        if (ApiClient.Instance != null && cost > 0)
            ApiClient.Instance.AddLocalCredits(cost);
        UpdateHUD();
    }

    private void UpdateHUD()
    {
        scoreText.text = $"Score: {score}";
        creditsText.text = $"Credits: {(ApiClient.Instance != null ? ApiClient.Instance.Credits : 0)}";
        healthText.text = $"HP: {health}";
    }
}