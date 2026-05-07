using UnityEngine;

public class PlayerController : MonoBehaviour
{
    public float speed = 6f;
    public float fireRate = 0.25f;
    public GameObject bulletPrefab;
    public Transform firePoint; // hijo del Player con offset hacia arriba

    private Rigidbody2D rb;
    private float lastShot;

    void Start()
    {
        rb = GetComponent<Rigidbody2D>();
    }

    void Update()
    {
        // Movimiento
        float h = Input.GetAxisRaw("Horizontal");
        float v = Input.GetAxisRaw("Vertical");
        rb.velocity = new Vector2(h, v).normalized * speed;

        // Disparo
        if (Input.GetKey(KeyCode.Space) && Time.time - lastShot > fireRate)
        {
            lastShot = Time.time;
            Instantiate(bulletPrefab, firePoint.position, Quaternion.identity);
        }

        // Tienda
        if (Input.GetKeyDown(KeyCode.T))
            GameManager.Instance.ToggleShop();
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        if (other.CompareTag("Enemy"))
        {
            Destroy(other.gameObject);
            GameManager.Instance.TakeDamage();
        }
    }
}