using UnityEngine;

public class Enemy : MonoBehaviour
{
    public float speed = 2f;
    public GameObject powerUpPrefab;
    [Range(0f, 1f)] public float dropChance = 0.3f;

    void Start()
    {
        GetComponent<Rigidbody2D>().velocity = Vector2.down * speed;
        Destroy(gameObject, 10f); // limpieza si sale de pantalla
    }

    public void Die()
    {
        GameManager.Instance.AddScore(10);

        if (Random.value < dropChance && powerUpPrefab != null)
            Instantiate(powerUpPrefab, transform.position, Quaternion.identity);

        Destroy(gameObject);
    }
}