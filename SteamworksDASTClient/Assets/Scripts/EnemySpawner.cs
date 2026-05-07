using UnityEngine;

public class EnemySpawner : MonoBehaviour
{
    public GameObject enemyPrefab;
    public float spawnInterval = 1.2f;
    public float xRange = 7f;
    public float ySpawn = 6f;

    private float timer;

    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= spawnInterval)
        {
            timer = 0f;
            float x = Random.Range(-xRange, xRange);
            Instantiate(enemyPrefab, new Vector3(x, ySpawn, 0), Quaternion.identity);
        }
    }
}