using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public class Item : MonoBehaviour, IPointerDownHandler ,IPointerEnterHandler,IPointerExitHandler
{
    public Vector2Int size;
    public int angle;
    public string[] tags;
    public bool canStore;//,isSpot;
    internal bool isShowing;
    internal Item itemOnSpot;
    // public Vector2Int containerSize;
    internal List<Item> itemHelds;
   // internal RectTransform GUI;
    void Start()
    {
        inventoryManager = GameObject.Find("Player").GetComponent<PlayerInventory>();
    }
    internal List<ItemSpot> mySpots;
    void Update()
    {
    }
    internal void rotate()
    {
        if(!canStore || (canStore && !isShowing))
        transform.RotateAround(Input.mousePosition, transform.forward, 90);
    }
    PlayerInventory inventoryManager;
    float lastClick;
    public void OnPointerDown(PointerEventData eventData)
    {
        if (isShowing) return;
        if (canStore)
        {
            if (Time.time - lastClick < 0.5f)
            {
                Debug.Log(name);
                inventoryManager.insantiateGUI(this);
            }
            lastClick = Time.time;
        }
        GetComponent<Image>().raycastTarget = false;
        foreach (Transform t in transform) t.GetComponent<Image>().raycastTarget = false;
        inventoryManager.startDraggin(this);
    }

    public void OnPointerEnter(PointerEventData eventData)
    {
        if (!canStore) return;
        if(isShowing)
        inventoryManager.mouseStorageEnter(this);
    }

    public void OnPointerExit(PointerEventData eventData)
    {
        if (!canStore) return;
        inventoryManager.mouseStorageExit(this);
    }
}
