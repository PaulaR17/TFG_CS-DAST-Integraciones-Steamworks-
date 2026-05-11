using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public class MainMenuController : MonoBehaviour
{
    [Header("Buttons")]
    public Button playButton;
    public Button quitButton;

    [Header("Scene")]
    [Tooltip("Nombre exacto de la escena del juego (debe estar en Build Settings)")]
    public string gameSceneName = "Game";

    void Start()
    {
        playButton.onClick.AddListener(OnPlay);
        quitButton.onClick.AddListener(OnQuit);
    }

    void OnPlay()
    {
        Debug.Log("[Menu] Iniciando partida...");
        SceneManager.LoadScene(gameSceneName);
    }

    void OnQuit()
    {
        Debug.Log("[Menu] Saliendo...");
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }
}